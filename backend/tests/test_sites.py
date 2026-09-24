"""
Tests for Site endpoints (INT-95).

Covers: CRUD sites, nested endpoint /clients/{id}/sites.

Run:
    cd backend/
    uv run pytest tests/test_sites.py -v --cov=app --cov-report=term-missing
"""

import httpx
import pytest
from httpx import ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import get_db
from app.core.security import create_access_token
from app.main import app
from app.models import Base
from app.models.client import Client
from app.models.site import Site
from app.models.user import Role, User

TEST_DB_URL = "sqlite+aiosqlite:///./test_tervo.db"
test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestSessionLocal = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)


async def _create_tables():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def _drop_tables():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def _get_test_db():
    async with TestSessionLocal() as session:
        yield session


@pytest.fixture
async def client():
    await _create_tables()
    app.dependency_overrides[get_db] = _get_test_db
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
    await _drop_tables()


@pytest.fixture
async def db():
    async with TestSessionLocal() as session:
        yield session


@pytest.fixture
async def tech_user(db: AsyncSession) -> User:
    user = User(
        username="tech_sites",
        email="tech@test.com",
        hashed_password="dummy",
        full_name="Tech Sites",
        role=Role.TECHNICIAN,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.fixture
def token(tech_user: User) -> str:
    return create_access_token(user_id=tech_user.id)


@pytest.fixture
def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class TestSites:
    """Tests for /sites/* and /clients/{id}/sites endpoints."""

    async def test_create_site(self, client, auth_header, db: AsyncSession):
        """POST /sites → 201."""
        c = Client(full_name="Site Owner", phone="0612345678", address="1 rue Test")
        db.add(c)
        await db.commit()
        await db.refresh(c)

        resp = await client.post(
            "/api/v1/sites",
            json={
                "client_id": c.id,
                "name": "Agence Massy",
                "address": "10 rue de la Gare",
                "postal_code": "91300",
                "city": "Massy",
            },
            headers=auth_header,
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["name"] == "Agence Massy"
        assert data["client_id"] == c.id
        assert "id" in data

    async def test_create_site_minimal(self, client, auth_header, db: AsyncSession):
        """POST /sites with only required fields → 201."""
        c = Client(full_name="Minimal Owner", phone="0600000000", address="1 rue Test")
        db.add(c)
        await db.commit()
        await db.refresh(c)

        resp = await client.post(
            "/api/v1/sites",
            json={"client_id": c.id, "name": "Domicile", "address": "2 rue Test"},
            headers=auth_header,
        )
        assert resp.status_code == 201, resp.text

    async def test_create_site_invalid_client(self, client, auth_header):
        """POST /sites with unknown client → 404."""
        resp = await client.post(
            "/api/v1/sites",
            json={"client_id": 99999, "name": "X", "address": "addr"},
            headers=auth_header,
        )
        assert resp.status_code == 404

    async def test_create_site_no_auth(self, client):
        """POST /sites without auth → 401."""
        resp = await client.post(
            "/api/v1/sites",
            json={"client_id": 1, "name": "X", "address": "addr"},
        )
        assert resp.status_code == 401

    async def test_list_sites(self, client, auth_header, db: AsyncSession):
        """GET /sites → 200 + list."""
        c = Client(full_name="List Owner", phone="0611111111", address="addr")
        db.add(c)
        await db.commit()
        await db.refresh(c)

        for i in range(3):
            db.add(
                Site(
                    client_id=c.id,
                    name=f"Site {i}",
                    address=f"{i} rue Test",
                    city="Paris",
                )
            )
        await db.commit()

        resp = await client.get("/api/v1/sites", headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 3

    async def test_get_site_by_id(self, client, auth_header, db: AsyncSession):
        """GET /sites/{id} → 200."""
        c = Client(full_name="Get Owner", phone="0622222222", address="addr")
        db.add(c)
        await db.commit()
        await db.refresh(c)

        s = Site(client_id=c.id, name="Get Site", address="addr")
        db.add(s)
        await db.commit()
        await db.refresh(s)

        resp = await client.get(f"/api/v1/sites/{s.id}", headers=auth_header)
        assert resp.status_code == 200
        assert resp.json()["name"] == "Get Site"

    async def test_get_site_not_found(self, client, auth_header):
        """GET /sites/99999 → 404."""
        resp = await client.get("/api/v1/sites/99999", headers=auth_header)
        assert resp.status_code == 404

    async def test_update_site(self, client, auth_header, db: AsyncSession):
        """PATCH /sites/{id} → 200."""
        c = Client(full_name="Update Owner", phone="0633333333", address="addr")
        db.add(c)
        await db.commit()
        await db.refresh(c)

        s = Site(client_id=c.id, name="Old Site", address="addr")
        db.add(s)
        await db.commit()
        await db.refresh(s)

        resp = await client.patch(
            f"/api/v1/sites/{s.id}",
            json={"name": "New Site", "city": "Lyon"},
            headers=auth_header,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "New Site"
        assert data["city"] == "Lyon"

    async def test_delete_site(self, client, auth_header, db: AsyncSession):
        """DELETE /sites/{id} → 204."""
        c = Client(full_name="Delete Owner", phone="0644444444", address="addr")
        db.add(c)
        await db.commit()
        await db.refresh(c)

        s = Site(client_id=c.id, name="To Delete", address="addr")
        db.add(s)
        await db.commit()
        await db.refresh(s)

        resp = await client.delete(f"/api/v1/sites/{s.id}", headers=auth_header)
        assert resp.status_code == 204

    async def test_delete_site_not_found(self, client, auth_header):
        """DELETE /sites/99999 → 404."""
        resp = await client.delete("/api/v1/sites/99999", headers=auth_header)
        assert resp.status_code == 404

    async def test_client_sites_two_sites(self, client, auth_header, db: AsyncSession):
        """GET /clients/{id}/sites → the 2 sites of the client are listed (AC)."""
        c = Client(full_name="Two Sites Owner", phone="0655555555", address="addr")
        db.add(c)
        await db.commit()
        await db.refresh(c)

        db.add(Site(client_id=c.id, name="Agence Massy", address="10 rue A"))
        db.add(Site(client_id=c.id, name="Agence Palaiseau", address="20 rue B"))
        await db.commit()

        resp = await client.get(
            f"/api/v1/clients/{c.id}/sites", headers=auth_header
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["total"] == 2
        names = {s["name"] for s in data["items"]}
        assert names == {"Agence Massy", "Agence Palaiseau"}

    async def test_client_sites_not_found(self, client, auth_header):
        """GET /clients/99999/sites → 404."""
        resp = await client.get("/api/v1/clients/99999/sites", headers=auth_header)
        assert resp.status_code == 404
