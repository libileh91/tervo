"""
Tests for Checklist API endpoints (INT-18, INT-19, INT-21).

Covers: GET checklist, PUT single item, PUT batch, validation.

Run:
    cd backend/
    uv run pytest tests/test_checklist_api.py -v --cov=app --cov-report=term-missing
"""

from datetime import date, datetime, timezone

import httpx
import pytest
from httpx import ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import get_db
from app.core.security import create_access_token
from app.main import app
from app.models import Base
from app.models.checklist_item import ChecklistItem
from app.models.client import Client
from app.models.job import Job, JobStatus
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
        username="tech_check",
        email="tech@test.com",
        hashed_password="dummy",
        full_name="Tech Checklist",
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


@pytest.fixture
async def client_fixture(db: AsyncSession) -> Client:
    c = Client(full_name="Checklist Client", phone="0600000000", address="1 rue Test")
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return c


@pytest.fixture
async def job_with_checklist(
    db: AsyncSession, tech_user: User, client_fixture: Client
) -> Job:
    """Job with 3 pre + 2 post checklist items."""
    j = Job(
        client_id=client_fixture.id,
        technician_id=tech_user.id,
        title="Checklist Job",
        status=JobStatus.EN_COURS,
        scheduled_date=date.today(),
        started_at=datetime.now(timezone.utc),
    )
    db.add(j)
    await db.commit()
    await db.refresh(j)

    items = []
    for cat, label, pos in [
        ("pre_intervention", "EPI vérifié", 0),
        ("pre_intervention", "Zone sécurisée", 1),
        ("pre_intervention", "Outillage complet", 2),
        ("post_intervention", "Nettoyage effectué", 0),
        ("post_intervention", "Client informé", 1),
    ]:
        items.append(
            ChecklistItem(job_id=j.id, category=cat, label=label, position=pos)
        )
        db.add(items[-1])
    await db.commit()

    for item in items:
        await db.refresh(item)
    return j


class TestChecklistAPI:
    """Tests for /jobs/{id}/checklist endpoints."""

    async def test_get_checklist(self, client, auth_header, job_with_checklist):
        """GET /jobs/{id}/checklist → 200 + 5 items."""
        resp = await client.get(
            f"/api/v1/jobs/{job_with_checklist.id}/checklist",
            headers=auth_header,
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert len(data) == 5

    async def test_get_checklist_not_found(self, client, auth_header):
        """GET /jobs/99999/checklist → 404."""
        resp = await client.get("/api/v1/jobs/99999/checklist", headers=auth_header)
        assert resp.status_code == 404

    async def test_get_checklist_no_auth(self, client, job_with_checklist):
        """No auth → 401."""
        resp = await client.get(f"/api/v1/jobs/{job_with_checklist.id}/checklist")
        assert resp.status_code == 401

    async def test_update_item(
        self, client, auth_header, job_with_checklist, db: AsyncSession
    ):
        """PUT single item → 200."""
        # Fetch the first checklist item
        from sqlalchemy import select

        from app.models.checklist_item import ChecklistItem

        result = await db.execute(
            select(ChecklistItem)
            .where(ChecklistItem.job_id == job_with_checklist.id)
            .limit(1)
        )
        item = result.scalar_one()
        resp = await client.put(
            f"/api/v1/jobs/{job_with_checklist.id}/checklist/{item.id}",
            json={"checked": True, "note": "OK"},
            headers=auth_header,
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["checked"] is True
        assert data["note"] == "OK"

    async def test_update_item_not_found(self, client, auth_header, job_with_checklist):
        """PUT non-existent item → 404."""
        resp = await client.put(
            f"/api/v1/jobs/{job_with_checklist.id}/checklist/99999",
            json={"checked": True},
            headers=auth_header,
        )
        assert resp.status_code == 404

    async def test_batch_update(
        self, client, auth_header, job_with_checklist, db: AsyncSession
    ):
        """PUT batch → 200."""
        from sqlalchemy import select

        from app.models.checklist_item import ChecklistItem

        result = await db.execute(
            select(ChecklistItem)
            .where(ChecklistItem.job_id == job_with_checklist.id)
            .limit(3)
        )
        items = list(result.scalars().all())
        payload = [
            {"id": item.id, "checked": True, "note": f"OK-{i}"}
            for i, item in enumerate(items)
        ]
        resp = await client.put(
            f"/api/v1/jobs/{job_with_checklist.id}/checklist/batch",
            json={"items": payload},
            headers=auth_header,
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["updated"] == 3

    async def test_batch_update_empty(self, client, auth_header, job_with_checklist):
        """Empty batch → 200 + updated=0."""
        resp = await client.put(
            f"/api/v1/jobs/{job_with_checklist.id}/checklist/batch",
            json={"items": []},
            headers=auth_header,
        )
        assert resp.status_code == 200
        assert resp.json()["updated"] == 0

    async def test_complete_without_checklist(
        self, client, auth_header, job_with_checklist, db
    ):
        """Complete with unchecked items → 400."""
        # All items are unchecked by default
        resp = await client.put(
            f"/api/v1/jobs/{job_with_checklist.id}/complete",
            json={},
            headers=auth_header,
        )
        assert resp.status_code == 400
        assert "items non cochés" in resp.json()["detail"]
