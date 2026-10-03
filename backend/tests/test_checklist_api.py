"""
Tests for Checklist API endpoints (INT-18, INT-19, INT-21).

Covers: immutable snapshot reads, assigned technician result patches, validation.

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
from app.core.base import Base
from app.modules.interventions.models.checklist_item import ChecklistItem
from app.modules.interventions.models.checklist import InterventionChecklist
from app.modules.customers.models import Client, Site
from app.modules.interventions.models.intervention import Intervention, InterventionStatus
from app.modules.identity.models import Role, User

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
async def site_fixture(db: AsyncSession) -> Site:
    c = Client(full_name="Checklist Client", phone="0600000000", address="1 rue Test")
    db.add(c)
    await db.commit()
    await db.refresh(c)
    s = Site(client_id=c.id, name="Site Test", address="1 rue Test")
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return s


@pytest.fixture
async def intervention_with_checklist(
    db: AsyncSession, tech_user: User, site_fixture: Site
) -> Intervention:
    """Intervention with 3 pre + 2 post checklist items."""
    j = Intervention(
        site_id=site_fixture.id,
        technician_id=tech_user.id,
        title="Checklist Intervention",
        status=InterventionStatus.IN_PROGRESS,
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
            ChecklistItem(category=cat, label=label, position=pos)
        )
    db.add(InterventionChecklist(
        intervention_id=j.id, template_name="Checklist fixture",
        template_version=1, items=items,
    ))
    await db.commit()

    for item in items:
        await db.refresh(item)
    return j


class TestChecklistAPI:
    """Tests for /interventions/{id}/checklist endpoints."""

    async def test_get_checklist(self, client, auth_header, intervention_with_checklist):
        """GET /interventions/{id}/checklist → 200 + 5 items."""
        resp = await client.get(
            f"/api/v1/interventions/{intervention_with_checklist.id}/checklist",
            headers=auth_header,
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["intervention_id"] == intervention_with_checklist.id
        assert data["template_name"] == "Checklist fixture"
        assert data["template_version"] == 1
        assert len(data["items"]) == 5
        assert all(item["result"] is None for item in data["items"])
        again = await client.get(
            f"/api/v1/interventions/{intervention_with_checklist.id}/checklist",
            headers=auth_header,
        )
        assert again.json() == data  # Reads must not rebuild the snapshot.

    async def test_get_checklist_not_found(self, client, auth_header):
        """GET /interventions/99999/checklist → 404."""
        resp = await client.get("/api/v1/interventions/99999/checklist", headers=auth_header)
        assert resp.status_code == 404

    async def test_get_checklist_no_auth(self, client, intervention_with_checklist):
        """No auth → 401."""
        resp = await client.get(f"/api/v1/interventions/{intervention_with_checklist.id}/checklist")
        assert resp.status_code == 401

    async def test_update_item(
        self, client, auth_header, intervention_with_checklist, db: AsyncSession
    ):
        """Assigned technician patches result/comment without changing structure."""
        # Fetch the first checklist item
        from sqlalchemy import select

        from app.modules.interventions.models.checklist_item import ChecklistItem

        result = await db.execute(
            select(ChecklistItem)
            .join(InterventionChecklist)
            .where(InterventionChecklist.intervention_id == intervention_with_checklist.id)
            .limit(1)
        )
        item = result.scalar_one()
        resp = await client.patch(
            f"/api/v1/checklist-items/{item.id}",
            json={"result": "OK", "comment": "Verified"},
            headers=auth_header,
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["result"] == "OK"
        assert data["comment"] == "Verified"
        assert data["label"] == item.label
        assert data["category"] == item.category
        assert data["completed_at"] is not None
        cleared = await client.patch(
            f"/api/v1/checklist-items/{item.id}",
            json={"result": None}, headers=auth_header,
        )
        assert cleared.status_code == 200, cleared.text
        assert cleared.json()["result"] is None
        assert cleared.json()["completed_at"] is None
        assert cleared.json()["comment"] == "Verified"

    async def test_update_item_not_found(self, client, auth_header, intervention_with_checklist):
        """PATCH non-existent item → 404."""
        resp = await client.patch(
            "/api/v1/checklist-items/99999",
            json={"result": "OK"},
            headers=auth_header,
        )
        assert resp.status_code == 404

    async def test_patch_multiple_results(
        self, client, auth_header, intervention_with_checklist, db: AsyncSession
    ):
        """Independent V2 patches persist each result; no retired batch route."""
        from sqlalchemy import select

        from app.modules.interventions.models.checklist_item import ChecklistItem

        result = await db.execute(
            select(ChecklistItem)
            .join(InterventionChecklist)
            .where(InterventionChecklist.intervention_id == intervention_with_checklist.id)
            .limit(3)
        )
        items = list(result.scalars().all())
        for i, item in enumerate(items):
            resp = await client.patch(
                f"/api/v1/checklist-items/{item.id}",
                json={"result": "OK", "comment": f"OK-{i}"},
                headers=auth_header,
            )
            assert resp.status_code == 200, resp.text
            assert resp.json()["result"] == "OK"
            assert resp.json()["comment"] == f"OK-{i}"
        resp = await client.get(
            f"/api/v1/interventions/{intervention_with_checklist.id}/checklist",
            headers=auth_header,
        )
        assert resp.status_code == 200, resp.text
        stored = {item["id"]: item for item in resp.json()["items"]}
        assert len(stored) == 5
        assert sum(item["result"] is not None for item in stored.values()) == 3
        for i, item in enumerate(items):
            assert stored[item.id]["comment"] == f"OK-{i}"

    async def test_patch_rejects_structure(self, client, auth_header, intervention_with_checklist):
        """Snapshot labels are immutable, even for the assigned technician."""
        snapshot = await client.get(
            f"/api/v1/interventions/{intervention_with_checklist.id}/checklist",
            headers=auth_header,
        )
        item = snapshot.json()["items"][0]
        resp = await client.patch(
            f"/api/v1/checklist-items/{item['id']}",
            json={"label": "Mutated", "result": "OK"}, headers=auth_header,
        )
        assert resp.status_code == 422
        after = await client.get(
            f"/api/v1/interventions/{intervention_with_checklist.id}/checklist",
            headers=auth_header,
        )
        assert after.json() == snapshot.json()

    async def test_complete_without_checklist(
        self, client, auth_header, intervention_with_checklist, db
    ):
        """Complete with unchecked items → 400."""
        # All items are unchecked by default
        resp = await client.put(
            f"/api/v1/interventions/{intervention_with_checklist.id}/complete",
            json={"result": "RESOLVED"},
            headers=auth_header,
        )
        assert resp.status_code == 400
        assert "items non réalisés" in resp.json()["detail"]

    async def test_historical_missing_snapshot_read_is_pure(
        self, client, auth_header, intervention_with_checklist, db
    ):
        """Historical direct ORM rows return 404, never lazy-create defaults."""
        from sqlalchemy import func, select

        historical = Intervention(
            site_id=intervention_with_checklist.site_id,
            technician_id=intervention_with_checklist.technician_id,
            title="Historical without snapshot", scheduled_date=date.today(),
            status=InterventionStatus.PLANNED,
        )
        db.add(historical)
        await db.commit()
        before = await db.scalar(select(func.count()).select_from(InterventionChecklist))
        for _ in range(2):
            response = await client.get(
                f"/api/v1/interventions/{historical.id}/checklist",
                headers=auth_header,
            )
            assert response.status_code == 404
        assert await db.scalar(
            select(func.count()).select_from(InterventionChecklist)
        ) == before
