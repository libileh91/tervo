"""INT-94–97: physical chain, catalogue reuse and replacement history."""
import httpx
import pytest
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from app.core.database import get_db
from app.core.deps import get_current_user
from app.main import app
from app.models import Base
from app.models.client import Client
from app.models.site import Site
from app.models.user import Role, User
from app.models.product import Product
from app.models.equipment import Equipment
from app.models.intervention import Intervention


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
