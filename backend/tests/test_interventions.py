"""
Tests for Intervention endpoints (INT-09, INT-10, INT-11, INT-12).

Covers: CRUD interventions, start, complete, dashboard, filters.

Run:
    cd backend/
    uv run pytest tests/test_interventions.py -v --cov=app --cov-report=term-missing
"""

from datetime import date, datetime, timedelta, timezone

import httpx
import pytest
from httpx import ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import get_db
from app.core.security import create_access_token
from app.main import app
from app.models import Base
from app.models.checklist_item import ChecklistItem
from app.models.client import Client
from app.models.intervention import Intervention, InterventionStatus
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
        username="tech_interventions",
        email="tech@test.com",
        hashed_password="dummy",
        full_name="Tech Interventions",
        role=Role.TECHNICIAN,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.fixture
async def other_tech(db: AsyncSession) -> User:
    user = User(
        username="other_tech_interventions",
        email="other@test.com",
        hashed_password="dummy",
        full_name="Other Tech",
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
def other_token(other_tech: User) -> str:
    return create_access_token(user_id=other_tech.id)


@pytest.fixture
def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def other_auth_header(other_token: str) -> dict:
    return {"Authorization": f"Bearer {other_token}"}


@pytest.fixture
async def client_fixture(db: AsyncSession) -> Client:
    c = Client(full_name="Intervention Test Client", phone="0600000000", address="1 rue Test")
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return c


class TestInterventions:
    """Tests for /interventions/* endpoints."""

    async def test_create_intervention(
        self, client, auth_header, client_fixture, db: AsyncSession
    ):
        """POST /interventions → 201."""
        resp = await client.post(
            "/api/v1/interventions",
            json={
                "client_id": client_fixture.id,
                "title": "Nouvelle intervention",
                "description": "Description test",
                "scheduled_date": str(date.today()),
                "priority": "haute",
            },
            headers=auth_header,
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["title"] == "Nouvelle intervention"
        assert data["status"] == "PLANNED"
        assert data["priority"] == "haute"

    async def test_list_interventions(
        self, client, auth_header, client_fixture, db: AsyncSession, tech_user
    ):
        """GET /interventions → 200 + list."""
        for i in range(2):
            db.add(
                Intervention(
                    client_id=client_fixture.id,
                    technician_id=tech_user.id,
                    title=f"Intervention {i}",
                    status=InterventionStatus.PLANNED,
                    scheduled_date=date.today(),
                )
            )
        await db.commit()

        resp = await client.get("/api/v1/interventions", headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 2

    async def test_get_intervention_by_id(
        self, client, auth_header, client_fixture, db: AsyncSession, tech_user
    ):
        """GET /interventions/{id} → 200."""
        j = Intervention(
            client_id=client_fixture.id,
            technician_id=tech_user.id,
            title="Detail Intervention",
            status=InterventionStatus.PLANNED,
            scheduled_date=date.today(),
        )
        db.add(j)
        await db.commit()
        await db.refresh(j)

        resp = await client.get(f"/api/v1/interventions/{j.id}", headers=auth_header)
        assert resp.status_code == 200
        assert resp.json()["title"] == "Detail Intervention"

    async def test_get_intervention_not_found(self, client, auth_header):
        """GET /interventions/99999 → 404."""
        resp = await client.get("/api/v1/interventions/99999", headers=auth_header)
        assert resp.status_code == 404

    async def test_update_intervention(
        self, client, auth_header, client_fixture, db: AsyncSession, tech_user
    ):
        """PUT /interventions/{id} → 200."""
        j = Intervention(
            client_id=client_fixture.id,
            technician_id=tech_user.id,
            title="Old Title",
            status=InterventionStatus.PLANNED,
            scheduled_date=date.today(),
        )
        db.add(j)
        await db.commit()
        await db.refresh(j)

        resp = await client.put(
            f"/api/v1/interventions/{j.id}",
            json={"title": "New Title"},
            headers=auth_header,
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "New Title"

    async def test_delete_intervention(
        self, client, auth_header, client_fixture, db: AsyncSession, tech_user
    ):
        """DELETE /interventions/{id} → 204."""
        j = Intervention(
            client_id=client_fixture.id,
            technician_id=tech_user.id,
            title="To Delete",
            status=InterventionStatus.PLANNED,
            scheduled_date=date.today(),
        )
        db.add(j)
        await db.commit()
        await db.refresh(j)

        resp = await client.delete(f"/api/v1/interventions/{j.id}", headers=auth_header)
        assert resp.status_code == 204

    async def test_start_intervention(
        self, client, auth_header, client_fixture, db: AsyncSession, tech_user
    ):
        """PUT /interventions/{id}/start → 200 + status IN_PROGRESS."""
        j = Intervention(
            client_id=client_fixture.id,
            technician_id=tech_user.id,
            title="Startable",
            status=InterventionStatus.PLANNED,
            scheduled_date=date.today(),
        )
        db.add(j)
        await db.commit()
        await db.refresh(j)

        resp = await client.put(
            f"/api/v1/interventions/{j.id}/start",
            headers=auth_header,
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "IN_PROGRESS"

    async def test_start_intervention_already_started(
        self, client, auth_header, client_fixture, db: AsyncSession, tech_user
    ):
        """PUT /interventions/{id}/start on already started → 400."""
        j = Intervention(
            client_id=client_fixture.id,
            technician_id=tech_user.id,
            title="Already Started",
            status=InterventionStatus.IN_PROGRESS,
            scheduled_date=date.today(),
            started_at=datetime.now(timezone.utc),
        )
        db.add(j)
        await db.commit()
        await db.refresh(j)

        resp = await client.put(
            f"/api/v1/interventions/{j.id}/start",
            headers=auth_header,
        )
        assert resp.status_code == 400

    async def test_complete_intervention(
        self, client, auth_header, client_fixture, db: AsyncSession, tech_user
    ):
        """PUT /interventions/{id}/complete with checked checklist → 200."""
        j = Intervention(
            client_id=client_fixture.id,
            technician_id=tech_user.id,
            title="Completable",
            status=InterventionStatus.IN_PROGRESS,
            scheduled_date=date.today(),
            started_at=datetime.now(timezone.utc),
        )
        db.add(j)
        await db.commit()
        await db.refresh(j)

        # Add checked checklist items
        for cat, label in [
            ("pre_intervention", "Pre A"),
            ("post_intervention", "Post B"),
        ]:
            db.add(
                ChecklistItem(
                    intervention_id=j.id, category=cat, label=label, checked=True, position=0
                )
            )
        await db.commit()

        resp = await client.put(
            f"/api/v1/interventions/{j.id}/complete",
            json={"observations": "Done!"},
            headers=auth_header,
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["status"] == "COMPLETED"
        assert "review_share_token" in data
        assert "report_url" in data

    async def test_complete_intervention_not_in_progress(
        self, client, auth_header, client_fixture, db: AsyncSession, tech_user
    ):
        """PUT /interventions/{id}/complete on PLANNED → 400."""
        j = Intervention(
            client_id=client_fixture.id,
            technician_id=tech_user.id,
            title="Planifiée",
            status=InterventionStatus.PLANNED,
            scheduled_date=date.today(),
        )
        db.add(j)
        await db.commit()
        await db.refresh(j)

        resp = await client.put(
            f"/api/v1/interventions/{j.id}/complete",
            json={},
            headers=auth_header,
        )
        assert resp.status_code == 400

    async def test_wrong_technician(
        self, client, other_auth_header, client_fixture, db: AsyncSession, tech_user
    ):
        """Wrong tech → 403."""
        j = Intervention(
            client_id=client_fixture.id,
            technician_id=tech_user.id,
            title="Not Yours",
            status=InterventionStatus.PLANNED,
            scheduled_date=date.today(),
        )
        db.add(j)
        await db.commit()
        await db.refresh(j)

        resp = await client.put(
            f"/api/v1/interventions/{j.id}/start",
            headers=other_auth_header,
        )
        assert resp.status_code == 403

    async def test_no_auth(self, client, client_fixture, db: AsyncSession, tech_user):
        """No auth → 401."""
        j = Intervention(
            client_id=client_fixture.id,
            technician_id=tech_user.id,
            title="No Auth",
            status=InterventionStatus.PLANNED,
            scheduled_date=date.today(),
        )
        db.add(j)
        await db.commit()
        await db.refresh(j)

        resp = await client.put(f"/api/v1/interventions/{j.id}/start")
        assert resp.status_code == 401


class TestDashboard:
    """Tests for /dashboard/summary endpoint (INT-12)."""

    async def test_dashboard_empty(self, client, auth_header):
        """No interventions today → empty summary."""
        resp = await client.get("/api/v1/dashboard/summary", headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()
        assert data["today"]["interventions_total"] == 0
        assert data["next_intervention"] is None

    async def test_dashboard_with_interventions(
        self, client, auth_header, client_fixture, db: AsyncSession, tech_user
    ):
        """Interventions today → summary with counts."""
        for i in range(2):
            db.add(
                Intervention(
                    client_id=client_fixture.id,
                    technician_id=tech_user.id,
                    title=f"Intervention {i}",
                    status=InterventionStatus.PLANNED,
                    scheduled_date=date.today(),
                )
            )
        await db.commit()

        resp = await client.get("/api/v1/dashboard/summary", headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()
        assert data["today"]["interventions_total"] == 2
        assert data["next_intervention"] is not None
