"""INT-102 sale lifecycle and SaleLine-to-Installation provenance."""
import os
from uuid import uuid4
import httpx
import pytest
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from app.core.database import get_db
from app.core.deps import get_current_user
from app.main import app
from app.models import Base
from app.models.client import Client
from app.models.installation import Installation
from app.models.product import Product
from app.models.sale import Sale, SaleLine, SaleStatus
from app.models.site import Site
from app.models.user import Role, User


@pytest.fixture
async def context():
    postgres = os.environ.get("TERVO_SALE_TEST_DATABASE_URL")
    schema = "sale_test_" + uuid4().hex
    admin = None
    engine = None
    schema_created = False
    try:
        if postgres:
            admin = create_async_engine(postgres)
            async with admin.begin() as connection:
                await connection.execute(text(f'CREATE SCHEMA {schema}'))
            schema_created = True
            engine = create_async_engine(postgres, connect_args={'server_settings': {'search_path': schema}})
        else:
            engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with sessions() as db:
            client = Client(full_name="Client", phone="0102030405", address="Paris")
            db.add(client); await db.flush()
            site = Site(client_id=client.id, name="Maison", address="Paris")
            product = Product(reference="PAC", name="PAC", brand="Marque", model="M", category="PAC")
            db.add_all([site, product]); await db.commit()
            ids = client.id, site.id, product.id
        async def database():
            async with sessions() as db:
                yield db
        app.dependency_overrides[get_db] = database
        app.dependency_overrides[get_current_user] = lambda: User(role=Role.ADMIN)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
            yield ac, sessions, ids
    finally:
        app.dependency_overrides.clear()
        try:
            if engine is not None:
                await engine.dispose()
        finally:
            if admin is not None:
                try:
                    if schema_created:
                        async with admin.begin() as connection:
                            await connection.execute(text(f'DROP SCHEMA {schema} CASCADE'))
                finally:
                    await admin.dispose()


async def test_quantity_three_can_provenance_three_installations(context):
    ac, sessions, (client_id, site_id, product_id) = context
    response = await ac.post("/api/v1/sales", json={"client_id": client_id, "site_id": site_id,
        "sale_date": "2026-09-29", "lines": [{"product_id": product_id, "quantity": 3,
        "unit_price": "1250.00"}]})
    assert response.status_code == 201, response.text
    sale = response.json()
    assert sale["status"] == "DRAFT" and len(sale["lines"]) == 1
    line_id = sale["lines"][0]["id"]
    assert (await ac.post(f"/api/v1/sales/{sale['id']}/confirm")).json()["status"] == "CONFIRMED"
    installation_ids = []
    for _ in range(3):
        result = await ac.post("/api/v1/installations", json={"site_id": site_id, "sale_line_id": line_id})
        assert result.status_code == 201, result.text
        installation_ids.append(result.json()["id"])
    assert (await ac.post(f"/api/v1/installations/{installation_ids[0]}/start")).status_code == 200
    completed = await ac.post(f"/api/v1/installations/{installation_ids[0]}/complete", json={
        "installation_date": "2026-09-29", "equipment": {"mode": "create", "product_id": product_id,
        "serial_number": "SOLD-001"}})
    assert completed.status_code == 200, completed.text
    assert completed.json()["sale_line_id"] == line_id
    assert completed.json()["equipment"]["product_id"] == product_id
    rejected = await ac.post("/api/v1/installations", json={"site_id": site_id, "sale_line_id": line_id})
    assert rejected.status_code == 409
    async with sessions() as db:
        assert await db.scalar(select(func.count(Installation.id)).where(Installation.sale_line_id == line_id)) == 3


async def test_confirmation_requires_line_and_unknown_references(context):
    ac, _, (client_id, site_id, product_id) = context
    sale = await ac.post("/api/v1/sales", json={"client_id": client_id, "site_id": site_id,
        "sale_date": "2026-09-29"})
    assert sale.status_code == 201
    assert (await ac.post(f"/api/v1/sales/{sale.json()['id']}/confirm")).status_code == 409
    bad = await ac.post("/api/v1/sales", json={"client_id": client_id, "site_id": site_id,
        "sale_date": "2026-09-29", "lines": [{"product_id": 999, "quantity": 1, "unit_price": 1}]})
    assert bad.status_code == 404
    assert (await ac.post("/api/v1/installations", json={"site_id": site_id, "sale_line_id": 999})).status_code == 404


async def test_autonomous_installation_accepts_null_sale_line(context):
    ac, _, (_, site_id, _) = context
    response = await ac.post("/api/v1/installations", json={"site_id": site_id, "sale_line_id": None})
    assert response.status_code == 201, response.text
    assert response.json()["sale_line_id"] is None
