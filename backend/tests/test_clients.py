"""
Tests for Client endpoints (INT-05, INT-06).

Covers: CRUD clients, search, history.

Run:
    cd backend/
    uv run pytest tests/test_clients.py -v --cov=app --cov-report=term-missing
"""

import uuid
from datetime import date

import httpx
import pytest
from httpx import ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import get_db
from app.core.security import create_access_token
from app.main import app
from app.models import Base
from app.models.client import Client
from app.models.intervention import Intervention, InterventionStatus
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
        username="tech_clients",
        email="tech@test.com",
        hashed_password="dummy",
        full_name="Tech Clients",
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


class TestClients:
    """Tests for /clients/* endpoints."""

    async def test_create_client(self, client, auth_header):
        """POST /clients → 201."""
        resp = await client.post(
            "/api/v1/clients",
            json={
                "full_name": "Jean Dupont",
                "phone": "0612345678",
                "address": "10 rue de Paris",
                "email": "jean@email.com",
                "city": "Paris",
            },
            headers=auth_header,
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["full_name"] == "Jean Dupont"
        assert data["phone"] == "0612345678"
        assert "id" in data

    async def test_create_client_minimal(self, client, auth_header):
        """POST /clients with only required fields → 201."""
        resp = await client.post(
            "/api/v1/clients",
            json={
                "full_name": "Minimal Client",
                "phone": "0600000000",
                "address": "1 rue Test",
            },
            headers=auth_header,
        )
        assert resp.status_code == 201

    async def test_create_client_no_auth(self, client):
        """POST /clients without auth → 401."""
        resp = await client.post(
            "/api/v1/clients",
            json={"full_name": "X", "phone": "06", "address": "addr"},
        )
        assert resp.status_code == 401

    async def test_list_clients(self, client, auth_header, db: AsyncSession):
        """GET /clients → 200 + list."""
        for i in range(3):
            db.add(
                Client(
                    full_name=f"Client {i}",
                    phone=f"060000000{i}",
                    address=f"{i} rue Test",
                    city="Paris",
                )
            )
        await db.commit()

        resp = await client.get("/api/v1/clients", headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 3

    async def test_get_client_by_id(self, client, auth_header, db: AsyncSession):
        """GET /clients/{id} → 200."""
        c = Client(full_name="Get Test", phone="0611111111", address="addr")
        db.add(c)
        await db.commit()
        await db.refresh(c)

        resp = await client.get(f"/api/v1/clients/{c.id}", headers=auth_header)
        assert resp.status_code == 200
        assert resp.json()["full_name"] == "Get Test"

    async def test_get_client_not_found(self, client, auth_header):
        """GET /clients/99999 → 404."""
        resp = await client.get("/api/v1/clients/99999", headers=auth_header)
        assert resp.status_code == 404

    async def test_update_client(self, client, auth_header, db: AsyncSession):
        """PUT /clients/{id} → 200."""
        c = Client(full_name="Old Name", phone="0622222222", address="addr")
        db.add(c)
        await db.commit()
        await db.refresh(c)

        resp = await client.put(
            f"/api/v1/clients/{c.id}",
            json={"full_name": "New Name"},
            headers=auth_header,
        )
        assert resp.status_code == 200
        assert resp.json()["full_name"] == "New Name"

    async def test_delete_client(self, client, auth_header, db: AsyncSession):
        """DELETE /clients/{id} → 204."""
        c = Client(full_name="To Delete", phone="0633333333", address="addr")
        db.add(c)
        await db.commit()
        await db.refresh(c)

        resp = await client.delete(f"/api/v1/clients/{c.id}", headers=auth_header)
        assert resp.status_code == 204

    async def test_delete_client_not_found(self, client, auth_header):
        """DELETE /clients/99999 → 404."""
        resp = await client.delete("/api/v1/clients/99999", headers=auth_header)
        assert resp.status_code == 404

    async def test_site_history(
        self, client, auth_header, db: AsyncSession, tech_user
    ):
        """GET /sites/{id}/interventions → 200 + list."""
        c = Client(full_name="History", phone="0644444444", address="addr")
        db.add(c)
        await db.commit()
        await db.refresh(c)

        s = Site(client_id=c.id, name="History Site", address="addr")
        db.add(s)
        await db.commit()
        await db.refresh(s)

        for i in range(2):
            db.add(
                Intervention(
                    site_id=s.id,
                    technician_id=tech_user.id,
                    title=f"Intervention {i}",
                    status=InterventionStatus.PLANNED,
                    scheduled_date=date.today(),
                )
            )
        await db.commit()

        resp = await client.get(f"/api/v1/sites/{s.id}/interventions", headers=auth_header)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert len(data) >= 2
