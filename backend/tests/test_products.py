"""INT-96: catalogue lifecycle, validation, filtering and permissions."""
import httpx
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from app.core.database import get_db
from app.core.deps import get_current_user
from app.main import app
from app.models import Base
from app.models.user import Role, User

PAYLOAD = dict(reference="DAI-35", name="Perfera", brand="Daikin", model="FTXM35",
               category="Climatisation", characteristics={"power_kw": 3.5}, description="Test")

@pytest.fixture
async def client():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async def database():
        async with sessions() as session:
            yield session
    app.dependency_overrides[get_db] = database
    app.dependency_overrides[get_current_user] = lambda: User(role=Role.ADMIN)
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()

async def test_lifecycle(client):
    response = await client.post("/api/v1/products", json=PAYLOAD)
    assert response.status_code == 201
    product = response.json()
    assert product["active"] is True
    assert product["characteristics"] == {"power_kw": 3.5}
    url = f'/api/v1/products/{product["id"]}'
    response = await client.patch(url, json={"description": None, "characteristics": None, "name": "New"})
    assert response.status_code == 200
    assert response.json()["description"] is None
    assert response.json()["characteristics"] is None
    assert response.json()["reference"] == PAYLOAD["reference"]
    for _ in range(2):
        response = await client.post(url + "/deactivate")
        assert response.status_code == 200
        assert response.json()["active"] is False
    assert (await client.get(url)).status_code == 200
    assert (await client.delete(url)).status_code == 405
    assert (await client.get("/api/v1/products?active=true")).json()["total"] == 0
    assert (await client.get("/api/v1/products?active=false")).json()["total"] == 1
    assert (await client.patch(url, json={"active": True})).json()["active"] is True

async def test_unique_reference(client):
    await client.post("/api/v1/products", json=PAYLOAD)
    assert (await client.post("/api/v1/products", json=PAYLOAD)).status_code == 409
    second = (await client.post("/api/v1/products", json={**PAYLOAD, "reference": "OTHER"})).json()
    url = f'/api/v1/products/{second["id"]}'
    assert (await client.patch(url, json={"reference": PAYLOAD["reference"]})).status_code == 409
    assert (await client.get(url)).json()["reference"] == "OTHER"
    assert (await client.patch(url, json={"reference": "OTHER"})).status_code == 200

async def test_filters(client):
    await client.post("/api/v1/products", json=PAYLOAD)
    await client.post("/api/v1/products", json={**PAYLOAD, "reference": "B", "brand": "Other", "active": False})
    for query, total in (("search=ftxm", 2), ("brand=Daikin", 1), ("category=Climatisation", 2), ("active=false", 1), ("search=perfera&brand=Daikin&active=true", 1)):
        response = await client.get("/api/v1/products?" + query)
        assert response.status_code == 200
        assert response.json()["total"] == total
    response = (await client.get("/api/v1/products?limit=1&page=2")).json()
    assert response["total"] == 2 and response["pages"] == 2 and len(response["items"]) == 1
    assert (await client.get("/api/v1/products?search=%25")).json()["total"] == 0
    assert (await client.get("/api/v1/products?page=0")).status_code == 422

@pytest.mark.parametrize("field", ["reference", "name", "brand", "model", "category", "active"])
async def test_reject_null(client, field):
    product = (await client.post("/api/v1/products", json=PAYLOAD)).json()
    assert (await client.patch(f'/api/v1/products/{product["id"]}', json={field: None})).status_code == 422
    assert (await client.post("/api/v1/products", json={**PAYLOAD, field: None})).status_code == 422

async def test_validation_and_missing(client):
    assert (await client.post("/api/v1/products", json={**PAYLOAD, "reference": "  "})).status_code == 422
    assert (await client.post("/api/v1/products", json={**PAYLOAD, "characteristics": []})).status_code == 422
    assert (await client.get("/api/v1/products/999")).status_code == 404
    assert (await client.patch("/api/v1/products/999", json={"name": "X"})).status_code == 404
    assert (await client.post("/api/v1/products/999/deactivate")).status_code == 404

async def test_permissions(client):
    app.dependency_overrides[get_current_user] = lambda: User(role=Role.TECHNICIAN)
    assert (await client.get("/api/v1/products")).status_code == 200
    assert (await client.post("/api/v1/products", json=PAYLOAD)).status_code == 403
    assert (await client.patch("/api/v1/products/1", json={"active": False})).status_code == 403
    assert (await client.post("/api/v1/products/1/deactivate")).status_code == 403
    del app.dependency_overrides[get_current_user]
    assert (await client.get("/api/v1/products")).status_code in (401, 403)


def test_product_migration_round_trip():
    """Exercise the new revision independently of PostgreSQL-only older revisions."""
    import importlib.util
    from pathlib import Path
    import sqlalchemy as sa
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    path = Path(__file__).parents[1] / "alembic/versions/8d431c2a9601_add_product_table.py"
    spec = importlib.util.spec_from_file_location("product_revision", path)
    revision = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(revision)
    engine = sa.create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        revision.op = Operations(MigrationContext.configure(connection))
        revision.upgrade()
        table = sa.Table("product", sa.MetaData(), autoload_with=connection)
        values = {k: v for k, v in PAYLOAD.items() if k != "characteristics"}
        connection.execute(table.insert().values(**values))
        row = connection.execute(sa.select(table)).mappings().one()
        assert row["active"] is True and row["created_at"] is not None
        with pytest.raises(sa.exc.IntegrityError):
            connection.execute(table.insert().values(**values))
        revision.downgrade()
        assert "product" not in sa.inspect(connection).get_table_names()
    engine.dispose()
