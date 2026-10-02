"""INT-103 autonomous API, real JWT guards, integrity and transaction regressions."""
import asyncio
import os
from uuid import uuid4
import httpx
import pytest
from sqlalchemy import event, func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from app.core.database import get_db
from app.core.security import create_access_token
from app.main import app
from app.models import Base
from app.modules.customers.models import Client, Site
from app.modules.equipment.models import Equipment
from app.modules.installations.models import Installation
from app.modules.catalog.models import Product

from app.modules.identity.models import Role, User
from app.modules.installations.repository import InstallationRepository

PREFIX = "/api/v1/installations"
COMPLETE = {"installation_date": "2026-09-28", "commissioning_date": "2026-09-28",
            "equipment": {"mode": "create", "serial_number": "CUSTOMER-1"}}


@pytest.fixture
async def context(tmp_path):
    postgres = os.environ.get("TERVO_INSTALLATION_TEST_DATABASE_URL")
    schema = "installation_test_" + uuid4().hex
    admin = None
    if postgres:
        admin = create_async_engine(postgres)
        async with admin.begin() as connection:
            await connection.execute(text(f'CREATE SCHEMA {schema}'))
        engine = create_async_engine(postgres, connect_args={'server_settings': {'search_path': schema}})
    else:
        engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'installations.db'}")
        @event.listens_for(engine.sync_engine, "connect")
        def foreign_keys(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with sessions() as db:
        users = [User(username=role.value, email=f"{role.value}@test.fr", hashed_password="unused", role=role)
                 for role in Role]
        owner = Client(full_name="Owner", phone="0102030405", address="Paris")
        db.add_all([*users, owner]); await db.flush()
        sites = [Site(client_id=owner.id, name=name, address=name) for name in ("A", "B")]
        product = Product(reference="P", name="PAC", model="M", brand="B", category="PAC")
        db.add_all([*sites, product]); await db.commit()
        ids = (owner.id, sites[0].id, sites[1].id, product.id)
        tokens = {user.role.value: {"Authorization": "Bearer " + create_access_token(user.id)} for user in users}
    async def database():
        async with sessions() as db:
            yield db
    app.dependency_overrides[get_db] = database
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test",
                                     headers=tokens["technician"]) as ac:
            yield ac, sessions, ids, tokens
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()
        if admin is not None:
            async with admin.begin() as connection:
                await connection.execute(text(f'DROP SCHEMA {schema} CASCADE'))
            await admin.dispose()


async def scheduled(ac, site):
    response = await ac.post(PREFIX, json={"site_id": site})
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def started(ac, site):
    installation_id = await scheduled(ac, site)
    response = await ac.post(f"{PREFIX}/{installation_id}/start")
    assert response.status_code == 200, response.text
    return installation_id


async def test_autonomous_create_and_reads(context):
    ac, sessions, (_, site, _, product), _ = context
    response = await ac.post(PREFIX, json={"site_id": site, "technician_notes": "Matériel client",
        "scheduled_start": "2026-09-28T10:00:00+02:00", "scheduled_end": "2026-09-28T09:00:00Z"})
    assert response.status_code == 201, response.text
    installation = response.json()
    assert installation["status"] == "SCHEDULED" and installation["equipment"] is None
    assert installation["scheduled_start"] == "2026-09-28T08:00:00"
    assert installation["sale_line_id"] is None
    async with sessions() as db:
        assert await db.scalar(select(func.count(Equipment.id))) == 0
    url = f'{PREFIX}/{installation["id"]}'
    running = (await ac.post(url + "/start")).json()
    assert running["started_at"] and running["completed_at"] is None
    response = await ac.post(url + "/complete", json={**COMPLETE,
        "equipment": {**COMPLETE["equipment"], "product_id": product}})
    assert response.status_code == 200, response.text
    done = response.json()
    assert done["status"] == "COMPLETED" and done["completed_at"] >= done["started_at"]
    equipment = done["equipment"]
    assert equipment["installation_id"] == installation["id"] and equipment["site_id"] == site
    assert equipment["product_id"] == product and equipment["lifecycle_status"] == "ACTIVE"
    assert equipment["installed_at"] == done["installation_date"]
    assert equipment["commissioned_at"] == done["commissioning_date"]
    assert (await ac.get(url)).json() == done
    listing = (await ac.get(PREFIX, params={"site_id": site, "status": "COMPLETED", "page_size": 1})).json()
    assert listing["total"] == 1 and listing["items"] == [done]
    assert (await ac.get(PREFIX, params={"page": 2, "page_size": 1})).json()["items"] == []
    assert (await ac.get(PREFIX + "?status=PLANNED")).status_code == 422
    assert "stock" not in Base.metadata.tables


@pytest.mark.parametrize("payload,code", [({},422), ({"site_id":None},422), ({"site_id":999},404),
    ({"site_id":1,"sale_line_id":999},404), ({"site_id":1,"sale_line_id":None},201),
    ({"site_id":1,"status":"COMPLETED"},422),
    ({"site_id":1,"scheduled_end":"2026-09-28T08:00:00"},422),
    ({"site_id":1,"scheduled_start":"2026-09-28T10:00:00","scheduled_end":"2026-09-28T09:00:00"},422)])
async def test_creation_validation(context, payload, code):
    ac, sessions, _, _ = context
    assert (await ac.post(PREFIX, json=payload)).status_code == code
    async with sessions() as db:
        assert await db.scalar(select(func.count(Installation.id))) == (1 if code == 201 else 0)


@pytest.mark.parametrize("body", [{}, {"installation_date":"2026-09-28"},
    {**COMPLETE,"equipment":{"mode":"attach"}},
    {**COMPLETE,"equipment":{"mode":"create","equipment_id":1}},
    {**COMPLETE,"equipment":{"mode":"create","lifecycle_status":"PLANNED"}},
    {**COMPLETE,"sale_line_id":1}, {**COMPLETE,"commissioning_date":"2026-09-27"}])
async def test_explicit_completion_contract(context, body):
    ac, _, (_, site, _, _), _ = context
    installation_id = await started(ac, site)
    assert (await ac.post(f"{PREFIX}/{installation_id}/complete", json=body)).status_code == 422
    assert (await ac.get(f"{PREFIX}/{installation_id}")).json()["status"] == "IN_PROGRESS"


@pytest.mark.parametrize("initial", ["SCHEDULED", "IN_PROGRESS", "COMPLETED", "CANCELLED"])
@pytest.mark.parametrize("action", ["start", "cancel", "complete"])
async def test_transition_matrix(context, initial, action):
    ac, sessions, (_, site, _, _), _ = context
    installation_id = await scheduled(ac, site)
    url = f"{PREFIX}/{installation_id}"
    if initial in ("IN_PROGRESS", "COMPLETED"):
        await ac.post(url + "/start")
    if initial == "COMPLETED":
        assert (await ac.post(url + "/complete", json=COMPLETE)).status_code == 200
    if initial == "CANCELLED":
        await ac.post(url + "/cancel")
    before = (await ac.get(url)).json()
    allowed = (initial, action) in {("SCHEDULED","start"),("SCHEDULED","cancel"),
                                    ("IN_PROGRESS","cancel"),("IN_PROGRESS","complete")}
    response = await ac.post(url + "/" + action, **({"json":COMPLETE} if action == "complete" else {}))
    assert response.status_code == (200 if allowed else 409), response.text
    if not allowed:
        assert (await ac.get(url)).json() == before
    async with sessions() as db:
        count = await db.scalar(select(func.count(Equipment.id)))
        assert count == int(initial == "COMPLETED" or (allowed and action == "complete"))


async def test_attach_preserves_equipment_and_prevents_reuse(context):
    ac, sessions, (_, site, _, product), _ = context
    old = (await ac.post('/api/v1/equipment', json={"site_id":site,"product_id":product,
        "serial_number":"HISTORIC","notes":"Keep me"})).json()
    installation_id = await started(ac, site)
    body = {**COMPLETE, "equipment":{"mode":"attach","equipment_id":old["id"]}}
    result = await ac.post(f"{PREFIX}/{installation_id}/complete", json=body)
    assert result.status_code == 200, result.text
    attached = result.json()["equipment"]
    for key in ("id","site_id","product_id","serial_number","notes","lifecycle_status"):
        assert attached[key] == old[key]
    second = await started(ac, site)
    assert (await ac.post(f"{PREFIX}/{second}/complete", json=body)).status_code == 409
    assert (await ac.get(f"{PREFIX}/{second}")).json()["status"] == "IN_PROGRESS"
    async with sessions() as db:
        assert await db.scalar(select(func.count(Equipment.id))) == 1


@pytest.mark.parametrize("case,code", [("missing",404),("other_site",422),("RETIRED",409),
    ("OUT_OF_SERVICE",409),("dates",409),("product",404)])
async def test_failed_completion_rolls_back(context, case, code):
    ac, sessions, (_, site, other, _), _ = context
    installation_id = await started(ac, site)
    body = {**COMPLETE, "equipment":{"mode":"attach","equipment_id":999}}
    if case not in ("missing","product"):
        values = {"site_id": other if case == "other_site" else site}
        if case in ("RETIRED","OUT_OF_SERVICE"):
            values["lifecycle_status"] = case
        if case == "dates":
            values["installed_at"] = "2000-01-01"
        equipment = (await ac.post('/api/v1/equipment', json=values)).json()
        body["equipment"]["equipment_id"] = equipment["id"]
    if case == "product":
        body["equipment"] = {"mode":"create","product_id":999}
    assert (await ac.post(f"{PREFIX}/{installation_id}/complete", json=body)).status_code == code
    async with sessions() as db:
        installation = await db.get(Installation, installation_id)
        assert installation.status == "IN_PROGRESS" and installation.completed_at is None
        assert installation.installation_date is None
        assert await db.scalar(select(func.count(Equipment.id)).where(Equipment.installation_id.is_not(None))) == 0


@pytest.mark.parametrize("mode", ["create", "attach"])
async def test_exception_after_equipment_write_rolls_back(context, monkeypatch, mode):
    ac, sessions, (_, site, _, _), _ = context
    installation_id = await started(ac, site)
    body = COMPLETE
    method = "create_equipment" if mode == "create" else "attach_equipment"
    if mode == "attach":
        equipment = (await ac.post('/api/v1/equipment', json={"site_id":site})).json()
        body = {**COMPLETE,"equipment":{"mode":"attach","equipment_id":equipment["id"]}}
    original = getattr(InstallationRepository, method)
    async def fail_after_write(self, *args, **kwargs):
        await original(self, *args, **kwargs)
        raise RuntimeError("Injected failure after equipment write")
    monkeypatch.setattr(InstallationRepository, method, fail_after_write)
    with pytest.raises(RuntimeError, match="Injected failure"):
        await ac.post(f"{PREFIX}/{installation_id}/complete", json=body)
    async with sessions() as db:
        installation = await db.get(Installation, installation_id)
        assert installation.status == "IN_PROGRESS" and installation.completed_at is None
        assert installation.installation_date is None
        assert await db.scalar(select(func.count(Equipment.id))) == int(mode == "attach")
        assert await db.scalar(select(func.count(Equipment.id)).where(Equipment.installation_id.is_not(None))) == 0


async def test_concurrent_closure_creates_only_one_equipment(context):
    ac, sessions, (_, site, _, _), _ = context
    installation_id = await started(ac, site)
    responses = await asyncio.gather(*[ac.post(f"{PREFIX}/{installation_id}/complete", json=COMPLETE) for _ in range(2)])
    assert sorted(r.status_code for r in responses) == [200,409]
    async with sessions() as db:
        assert await db.scalar(select(func.count(Equipment.id))) == 1


async def test_same_equipment_competing_installations(context):
    ac, _, (_, site, _, _), _ = context
    equipment = (await ac.post('/api/v1/equipment', json={"site_id":site})).json()
    ids = [await started(ac, site), await started(ac, site)]
    body = {**COMPLETE,"equipment":{"mode":"attach","equipment_id":equipment["id"]}}
    responses = await asyncio.gather(*[ac.post(f"{PREFIX}/{i}/complete", json=body) for i in ids])
    assert sorted(r.status_code for r in responses) == [200,409]

    statuses = [(await ac.get(f"{PREFIX}/{i}")).json()["status"] for i in ids]
    assert sorted(statuses) == ["COMPLETED","IN_PROGRESS"]


async def test_cancel_competing_with_complete(context):
    ac, sessions, (_, site, _, _), _ = context
    installation_id = await started(ac, site)
    url = f"{PREFIX}/{installation_id}"
    responses = await asyncio.gather(ac.post(url + '/cancel'), ac.post(url + '/complete', json=COMPLETE))
    assert sorted(r.status_code for r in responses) == [200,409]
    final = (await ac.get(url)).json()
    async with sessions() as db:
        assert await db.scalar(select(func.count(Equipment.id))) == int(final['status'] == 'COMPLETED')
    assert (final['completed_at'] is not None) == (final['status'] == 'COMPLETED')


async def test_replaced_equipment_cannot_be_attached(context):
    ac, _, (_, site, _, _), _ = context
    old = (await ac.post('/api/v1/equipment', json={'site_id':site})).json()
    assert (await ac.post(f'/api/v1/equipment/{old["id"]}/replace', json={})).status_code == 201
    installation_id = await started(ac, site)
    body = {**COMPLETE,'equipment':{'mode':'attach','equipment_id':old['id']}}
    assert (await ac.post(f'{PREFIX}/{installation_id}/complete', json=body)).status_code == 409
    assert (await ac.get(f'{PREFIX}/{installation_id}')).json()['status'] == 'IN_PROGRESS'


async def test_integrity_conflict_during_create_is_atomic(context):
    ac, sessions, (_, site, _, _), _ = context
    installation_id = await started(ac, site)
    # Simulate a preexisting inconsistent write outside the lifecycle service.
    async with sessions() as db:
        db.add(Equipment(site_id=site, installation_id=installation_id))
        await db.commit()
    response = await ac.post(f'{PREFIX}/{installation_id}/complete', json=COMPLETE)
    assert response.status_code == 409
    async with sessions() as db:
        installation = await db.get(Installation, installation_id)
        assert installation.status == 'IN_PROGRESS' and installation.completed_at is None
        assert await db.scalar(select(func.count(Equipment.id))) == 1


async def test_database_constraints_and_history_protection(context):
    ac, sessions, (owner, site, _, _), _ = context
    installation_id = await started(ac, site)
    assert (await ac.delete(f"/api/v1/sites/{site}")).status_code == 409
    assert (await ac.delete(f"/api/v1/clients/{owner}")).status_code == 409
    await ac.post(f"{PREFIX}/{installation_id}/complete", json=COMPLETE)
    for target in (installation_id, 999):
        async with sessions() as db:
            db.add(Equipment(site_id=site, installation_id=target))
            with pytest.raises(IntegrityError):
                await db.commit()
            await db.rollback()
    async with sessions() as db:
        with pytest.raises(IntegrityError):
            await db.execute(text("DELETE FROM installation WHERE id=:id"), {"id": installation_id})
        await db.rollback()
        with pytest.raises(IntegrityError):
            await db.execute(text("UPDATE installation SET status='PLANNED'"))
        await db.rollback()
        db.add_all([Equipment(site_id=site), Equipment(site_id=site)])
        await db.commit()
    assert (await ac.post('/api/v1/equipment', json={"site_id":site,"installation_id":installation_id})).status_code == 422


@pytest.mark.parametrize("method,path", [("GET",""),("POST",""),("GET","/999"),
    ("POST","/999/start"),("POST","/999/cancel"),("POST","/999/complete")])
async def test_all_routes_require_real_active_jwt(context, method, path):
    ac, sessions, _, _ = context
    ac.headers.pop("Authorization")
    assert (await ac.request(method,PREFIX+path)).status_code in (401,403)
    ac.headers["Authorization"] = "Bearer invalid"
    assert (await ac.request(method,PREFIX+path)).status_code == 401
    async with sessions() as db:
        user = await db.scalar(select(User).where(User.role == Role.TECHNICIAN))
        user.is_active = False
        await db.commit()
        ac.headers["Authorization"] = "Bearer " + create_access_token(user.id)
    assert (await ac.request(method,PREFIX+path)).status_code == 401


async def test_admin_and_unknown_resources(context):
    ac, _, (_, site, _, _), tokens = context
    ac.headers.update(tokens['admin'])
    await scheduled(ac, site)
    assert (await ac.get(PREFIX + '/999')).status_code == 404
    for action in ('start','cancel','complete'):
        response = await ac.post(PREFIX + '/999/' + action, **({'json':COMPLETE} if action=='complete' else {}))
        assert response.status_code == 404
