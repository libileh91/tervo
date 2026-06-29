"""
Tests for Auth endpoints (INT-02, INT-03).

Covers: login, refresh, me, unauthorized access.

Run:
    cd backend/
    uv run pytest tests/test_auth.py -v --cov=app --cov-report=term-missing
"""

import httpx
import pytest
from httpx import ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import get_db
from app.core.security import create_access_token, get_password_hash
from app.main import app
from app.models import Base
from app.models.user import Role, User

TEST_DB_URL = "sqlite+aiosqlite:///./test_resq.db"
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
async def test_user(db: AsyncSession) -> User:
    """Create a technician user with known password."""
    user = User(
        username="tech_login",
        email="tech@resq.app",
        hashed_password=get_password_hash("secret123"),
        full_name="Tech Login",
        role=Role.TECHNICIAN,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


class TestAuth:
    """Tests for /auth/* endpoints."""

    async def test_login_success(self, client, test_user):
        """Valid credentials → 200 + tokens."""
        resp = await client.post(
            "/api/v1/auth/login",
            json={"username": "tech_login", "password": "secret123"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] == 1800

    async def test_login_wrong_password(self, client, test_user):
        """Wrong password → 401."""
        resp = await client.post(
            "/api/v1/auth/login",
            json={"username": "tech_login", "password": "wrong"},
        )
        assert resp.status_code == 401

    async def test_login_unknown_user(self, client):
        """Unknown user → 401."""
        resp = await client.post(
            "/api/v1/auth/login",
            json={"username": "nobody", "password": "x"},
        )
        assert resp.status_code == 401

    async def test_login_inactive_user(self, client, db: AsyncSession):
        """Inactive user → 401."""
        user = User(
            username="inactive",
            email="inactive@resq.app",
            hashed_password=get_password_hash("pwd"),
            full_name="Inactive",
            role=Role.TECHNICIAN,
            is_active=False,
        )
        db.add(user)
        await db.commit()

        resp = await client.post(
            "/api/v1/auth/login",
            json={"username": "inactive", "password": "pwd"},
        )
        assert resp.status_code == 401

    async def test_login_no_body(self, client):
        """Missing body → 422."""
        resp = await client.post("/api/v1/auth/login", json={})
        assert resp.status_code == 422

    async def test_refresh_success(self, client, test_user):
        """Valid refresh token → 200 + new tokens."""
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"username": "tech_login", "password": "secret123"},
        )
        refresh_token = login_resp.json()["refresh_token"]

        resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_refresh_invalid_token(self, client):
        """Invalid refresh token → 401."""
        resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid_token"},
        )
        assert resp.status_code == 401

    async def test_me_success(self, client, test_user):
        """GET /auth/me → 200 with user info."""
        token = create_access_token(user_id=test_user.id)
        resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["username"] == "tech_login"
        assert data["email"] == "tech@resq.app"
        assert data["role"] == "technician"
        assert data["is_active"] is True

    async def test_me_no_auth(self, client):
        """No token → 401."""
        resp = await client.get("/api/v1/auth/me")
        assert resp.status_code == 401

    async def test_me_invalid_token(self, client):
        """Invalid token → 401."""
        resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid"},
        )
        assert resp.status_code == 401

    async def test_me_update(self, client, test_user):
        """PUT /auth/me → 200."""
        token = create_access_token(user_id=test_user.id)
        resp = await client.put(
            "/api/v1/auth/me",
            json={"full_name": "Updated Name"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["full_name"] == "Updated Name"

        # Verify the name stuck
        resp2 = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp2.json()["full_name"] == "Updated Name"
