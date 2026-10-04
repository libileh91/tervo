"""INT-94–97/110: physical chain, catalogue reuse and replacement history."""
from datetime import date, datetime
from hashlib import sha256

import httpx
import pytest
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from app.core.database import get_db
from app.modules.identity.dependencies import get_current_user
from app.main import app
from app.core.base import Base
from app.modules.customers.models import Client, Site
from app.modules.identity.models import Role, User
from app.modules.catalog.models import Product
from app.modules.equipment.models import Equipment
from app.modules.interventions.models.intervention import Intervention
from app.modules.interventions.models.photo import Photo
from app.modules.installations.models import Installation, InstallationStatus
from app.modules.reports.models import Report, ReportVersion


@pytest.fixture
async def context():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    @event.listens_for(engine.sync_engine, "connect")
    def enable_fks(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with sessions() as db:
        user = User(username="equipment", email="equipment@test.fr", hashed_password="unused", role=Role.ADMIN)
        client = Client(full_name="Owner", phone="0102030405", address="Paris")
        db.add_all([user, client]); await db.flush()
        sites = [Site(client_id=client.id, name=n, address=n) for n in ("A", "B")]
        product = Product(reference="P1", name="PAC", model="M1", brand="B", category="PAC")
        db.add_all([*sites, product]); await db.commit()
        ids = (client.id, sites[0].id, sites[1].id, product.id)
    async def database():
        async with sessions() as db:
            yield db
    app.dependency_overrides[get_db] = database
    app.dependency_overrides[get_current_user] = lambda: user
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
            yield ac, sessions, ids
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


async def test_replacement_preserves_history_and_product_instances(context):
    ac, sessions, (client_id, site, _, product) = context
    payload = dict(site_id=site, product_id=product, serial_number="OLD")
    response = await ac.post("/api/v1/equipment", json=payload)
    assert response.status_code == 201
    old = response.json()
    intervention = await ac.post("/api/v1/interventions", json=dict(site_id=site, equipment_id=old['id'],
        title="Entretien", scheduled_date="2026-09-24", under_warranty=True))
    assert intervention.status_code == 201
    assert intervention.json()['under_warranty'] is True
    response = await ac.post(f'/api/v1/equipment/{old["id"]}/replace', json=dict(new_product_id=product,
        serial_number="NEW", installation_date="2026-09-24"))
    assert response.status_code == 201
    new = response.json()
    assert new['id'] != old['id'] and new['site_id'] == site
    assert new['lifecycle_status'] == 'ACTIVE'
    old = (await ac.get(f'/api/v1/equipment/{old["id"]}')).json()
    assert old['replaced_by_id'] == new['id'] and old['lifecycle_status'] == 'REPLACED'
    history = (await ac.get(f'/api/v1/interventions/{intervention.json()["id"]}')).json()
    assert history['equipment_id'] == old['id']
    assert (await ac.post(f'/api/v1/products/{product}/deactivate')).status_code == 200
    assert (await ac.get(f'/api/v1/equipment?product_id={product}')).json()['total'] == 2
    assert (await ac.get(f'/api/v1/sites/{site}/equipment')).json()['total'] == 2
    assert (await ac.post(f'/api/v1/equipment/{old["id"]}/replace', json={})).status_code == 409
    assert (await ac.delete(f'/api/v1/sites/{site}')).status_code == 409
    assert (await ac.delete(f'/api/v1/clients/{client_id}')).status_code == 409
    async with sessions() as db:
        stored = await db.get(Intervention, history['id'])
        assert stored.equipment_id == old['id']
        assert len(list(await db.scalars(select(Equipment)))) == 2


async def test_site_consistency_and_nullable_intervention_link(context):
    ac, _, (_, site, other_site, _) = context
    equipment = (await ac.post('/api/v1/equipment', json={'site_id':site})).json()
    assert equipment['installation_id'] is None and equipment['product_id'] is None
    body = dict(site_id=other_site, title="Diagnostic", scheduled_date="2026-09-24")
    assert (await ac.post('/api/v1/interventions', json={**body, 'equipment_id':equipment['id']})).status_code == 422
    assert (await ac.post('/api/v1/interventions', json={**body, 'equipment_id':999})).status_code == 404
    response = await ac.post('/api/v1/interventions', json=body)
    assert response.status_code == 201 and response.json()['equipment_id'] is None
    url = f'/api/v1/interventions/{response.json()["id"]}'
    assert (await ac.put(url, json={'equipment_id': equipment['id']})).status_code == 422
    own = (await ac.post('/api/v1/interventions', json={**body, 'site_id':site, 'equipment_id':equipment['id']})).json()
    response = await ac.put(f'/api/v1/interventions/{own["id"]}', json={'equipment_id':None})
    assert response.status_code == 200 and response.json()['equipment_id'] is None


async def test_invalid_replacement_is_atomic(context):
    ac, _, (_, site, _, _) = context
    old = (await ac.post('/api/v1/equipment', json={'site_id':site})).json()
    assert (await ac.post(f'/api/v1/equipment/{old["id"]}/replace', json={'new_product_id':999})).status_code == 404
    assert (await ac.get('/api/v1/equipment')).json()['total'] == 1
    assert (await ac.get(f'/api/v1/equipment/{old["id"]}')).json()['lifecycle_status'] == 'ACTIVE'
    assert (await ac.get('/api/v1/equipment/999')).status_code == 404
    assert (await ac.get('/api/v1/sites/999/equipment')).status_code == 404
    assert (await ac.post('/api/v1/equipment', json={'site_id':999})).status_code == 404
    for state in ('PLANNED', 'REPLACED', 'invalid'):
        assert (await ac.post('/api/v1/equipment', json={'site_id':site, 'lifecycle_status':state})).status_code == 422
    retired = (await ac.post('/api/v1/equipment', json={'site_id':site, 'lifecycle_status':'RETIRED'})).json()
    assert (await ac.post(f'/api/v1/equipment/{retired["id"]}/replace', json={})).status_code == 409
    assert (await ac.get('/api/v1/equipment?lifecycle_status=RETIRED')).json()['total'] == 1
    assert (await ac.get('/api/v1/equipment?page_size=1&page=2')).json()['pages'] == 2
    assert (await ac.delete(f'/api/v1/equipment/{old["id"]}')).status_code == 405
    del app.dependency_overrides[get_current_user]
    assert (await ac.get('/api/v1/equipment')).status_code in (401,403)


async def test_int110_replacement_keeps_installation_intervention_photo_and_pdf(context):
    """One real API recipe over historical links; no PDF rerender and no migration."""
    ac, sessions, (_, site, _, product) = context
    pdf = b"%PDF-1.4\n% historical report\n"
    async with sessions() as db:
        installation = Installation(
            site_id=site, status=InstallationStatus.COMPLETED,
            installation_date=date(2020, 6, 1),
        )
        db.add(installation)
        await db.flush()
        old = Equipment(
            site_id=site, product_id=product, installation_id=installation.id,
            serial_number="OLD-100", installed_at=date(2020, 6, 1),
            warranty_start=date(2020, 6, 1), warranty_end=date(2025, 6, 1),
        )
        db.add(old)
        await db.flush()
        intervention = Intervention(
            site_id=site, equipment_id=old.id, title="Réparation ancienne",
            scheduled_date=date(2026, 9, 20), status="COMPLETED", result="PART_NEEDED",
        )
        db.add(intervention)
        await db.flush()
        photo = Photo(intervention_id=intervention.id, usage="BEFORE", file_path="/archive/old.jpg")
        report = Report(intervention_id=intervention.id)
        db.add_all([photo, report])
        await db.flush()
        db.add(ReportVersion(
            report_id=report.id, version=1, pdf=pdf, sha256=sha256(pdf).hexdigest(),
            size=len(pdf), generated_at=datetime(2026, 9, 20),
        ))
        await db.commit()
        old_id, intervention_id, installation_id = old.id, intervention.id, installation.id
        photo_id, report_id = photo.id, report.id

    url = f"/api/v1/equipment/{old_id}/replace"
    for payload, expected in (
        ({"serial_number": "  "}, 422),
        ({"serial_number": "old-100"}, 409),
        ({"warranty_start": "2031-01-01", "warranty_end": "2030-01-01"}, 422),
        ({"installation_date": "2026-10-15", "commissioned_at": "2026-10-14"}, 422),
        ({"new_product_id": 999999}, 404),
    ):
        response = await ac.post(url, json=payload)
        assert response.status_code == expected, response.text
    assert (await ac.get(f"/api/v1/equipment/{old_id}")).json()["lifecycle_status"] == "ACTIVE"
    assert (await ac.get("/api/v1/equipment", params={"site_id": site})).json()["total"] == 1

    response = await ac.post(url, json={
        "new_product_id": product, "serial_number": " NEW-200 ",
        "installation_date": "2026-10-15", "commissioned_at": "2026-10-16",
        "warranty_start": "2026-10-15", "warranty_end": "2030-10-15",
    })
    assert response.status_code == 201, response.text
    new = response.json()
    assert new["id"] != old_id and new["site_id"] == site
    assert new["serial_number"] == "NEW-200" and new["installed_at"] == "2026-10-15"
    assert new["commissioned_at"] == "2026-10-16"
    assert new["warranty_start"] == "2026-10-15" and new["warranty_end"] == "2030-10-15"
    assert new["installation_id"] is None and new["lifecycle_status"] == "ACTIVE"
    assert (await ac.post(url, json={})).status_code == 409

    previous = (await ac.get(f"/api/v1/equipment/{old_id}")).json()
    assert previous["replaced_by_id"] == new["id"] and previous["lifecycle_status"] == "REPLACED"
    assert previous["serial_number"] == "OLD-100"
    assert previous["warranty_end"] == "2025-06-01"
    assert previous["installation_id"] == installation_id
    detail = await ac.get(f"/api/v1/interventions/{intervention_id}")
    assert detail.status_code == 200, detail.text
    assert detail.json()["equipment_id"] == old_id
    assert [p["id"] for p in detail.json()["photos"]] == [photo_id]
    assert detail.json()["photos"][0]["file_url"].endswith("/old.jpg")
    assert (await ac.get(f"/api/v1/reports/{report_id}/versions/1")).content == pdf
    async with sessions() as db:
        assert (await db.get(Equipment, old_id)).installation_id == installation_id
        assert (await db.get(Equipment, new["id"])).installation_id is None
        historical_photo = await db.get(Photo, photo_id)
        assert historical_photo.intervention_id == intervention_id
        assert historical_photo.file_path == "/archive/old.jpg"
        assert (await db.get(Report, report_id)).intervention_id == intervention_id
        assert len(list(await db.scalars(select(Equipment)))) == 2
