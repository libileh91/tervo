"""
Targeted tests for remaining uncovered lines.

Run:
    cd backend/
    uv run pytest tests/test_additional.py -v --cov=app --cov-report=term-missing
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
        username="tech_extra",
        email="tech@test.com",
        hashed_password="dummy",
        full_name="Tech Extra",
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
        username="other_tech_extra",
        email="other@test.com",
        hashed_password="dummy",
        full_name="Other Extra",
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
    c = Client(full_name="Extra Test Client", phone="0600000000", address="1 rue Test")
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return c


@pytest.fixture
async def job_planifie(
    db: AsyncSession, tech_user: User, client_fixture: Client
) -> Job:
    j = Job(
        client_id=client_fixture.id,
        technician_id=tech_user.id,
        title="Extra Planifié",
        status=JobStatus.PLANIFIE,
        scheduled_date=date.today(),
    )
    db.add(j)
    await db.commit()
    await db.refresh(j)
    return j


@pytest.fixture
async def job_en_cours(
    db: AsyncSession, tech_user: User, client_fixture: Client
) -> Job:
    j = Job(
        client_id=client_fixture.id,
        technician_id=tech_user.id,
        title="Extra En Cours",
        status=JobStatus.EN_COURS,
        scheduled_date=date.today(),
        started_at=datetime.now(timezone.utc),
    )
    db.add(j)
    await db.commit()
    await db.refresh(j)
    return j


@pytest.fixture
async def job_termine(db: AsyncSession, tech_user: User, client_fixture: Client) -> Job:
    j = Job(
        client_id=client_fixture.id,
        technician_id=tech_user.id,
        title="Extra Terminé",
        status=JobStatus.TERMINE,
        scheduled_date=date.today(),
        started_at=datetime.now(timezone.utc) - timedelta(hours=2),
        completed_at=datetime.now(timezone.utc),
    )
    db.add(j)
    await db.commit()
    await db.refresh(j)
    return j


class TestMaterialsExtra:
    """Covers missing lines in materials API: 403 on PUT/DELETE, 404 on PUT/DELETE."""

    async def test_update_material_wrong_tech(
        self, client, other_auth_header, job_en_cours, db: AsyncSession
    ):
        """PUT material with wrong tech → 403."""
        from app.models.material import Material

        mat = Material(job_id=job_en_cours.id, name="Test", quantity="1")
        db.add(mat)
        await db.commit()
        await db.refresh(mat)

        resp = await client.put(
            f"/api/v1/jobs/{job_en_cours.id}/materials/{mat.id}",
            json={"quantity": "2"},
            headers=other_auth_header,
        )
        assert resp.status_code == 403

    async def test_delete_material_wrong_tech(
        self, client, other_auth_header, job_en_cours, db: AsyncSession
    ):
        """DELETE material with wrong tech → 403."""
        from app.models.material import Material

        mat = Material(job_id=job_en_cours.id, name="Test", quantity="1")
        db.add(mat)
        await db.commit()
        await db.refresh(mat)

        resp = await client.delete(
            f"/api/v1/jobs/{job_en_cours.id}/materials/{mat.id}",
            headers=other_auth_header,
        )
        assert resp.status_code == 403

    async def test_update_material_not_found(self, client, auth_header, job_en_cours):
        """PUT material 99999 → 404."""
        resp = await client.put(
            f"/api/v1/jobs/{job_en_cours.id}/materials/99999",
            json={"quantity": "2"},
            headers=auth_header,
        )
        assert resp.status_code == 404

    async def test_delete_material_not_found(self, client, auth_header, job_en_cours):
        """DELETE material 99999 → 404."""
        resp = await client.delete(
            f"/api/v1/jobs/{job_en_cours.id}/materials/99999",
            headers=auth_header,
        )
        assert resp.status_code == 404


class TestReportsExtra:
    """Covers missing lines in reports API: 403, 404."""

    async def test_report_wrong_tech(self, client, other_auth_header, job_termine):
        """Download report with wrong tech → 403."""
        resp = await client.get(
            f"/api/v1/jobs/{job_termine.id}/report/download",
            headers=other_auth_header,
        )
        assert resp.status_code == 403

    async def test_report_not_found(self, client, auth_header):
        """Download report for non-existent job → 404."""
        resp = await client.get(
            "/api/v1/jobs/99999/report/download",
            headers=auth_header,
        )
        assert resp.status_code == 404


class TestJobsExtra:
    """Covers uncovered complete_job paths: no checklist, already completed."""

    async def test_start_job_wrong_status(self, client, auth_header, job_termine):
        """Start already terminated job → 400."""
        resp = await client.put(
            f"/api/v1/jobs/{job_termine.id}/start",
            headers=auth_header,
        )
        assert resp.status_code == 400

    async def test_complete_job_without_checklist(
        self, client, auth_header, job_en_cours, db
    ):
        """Complete without adding checklist items → should succeed (no checklist = ok)."""
        resp = await client.put(
            f"/api/v1/jobs/{job_en_cours.id}/complete",
            json={},
            headers=auth_header,
        )
        # No checklist items → no validation → should succeed
        assert resp.status_code == 200

    async def test_complete_already_terminated(self, client, auth_header, job_termine):
        """Complete already terminated job → 400."""
        resp = await client.put(
            f"/api/v1/jobs/{job_termine.id}/complete",
            json={},
            headers=auth_header,
        )
        assert resp.status_code == 400


class TestChecklistExtra:
    """Covers missing lines in checklist API: 403, 404."""

    async def test_update_checklist_wrong_tech(
        self, client, other_auth_header, job_en_cours, db: AsyncSession
    ):
        """Update checklist with wrong tech → 403."""
        item = ChecklistItem(
            job_id=job_en_cours.id,
            category="pre_intervention",
            label="Test",
            position=0,
        )
        db.add(item)
        await db.commit()
        await db.refresh(item)

        resp = await client.put(
            f"/api/v1/jobs/{job_en_cours.id}/checklist/{item.id}",
            json={"checked": True},
            headers=other_auth_header,
        )
        assert resp.status_code == 403

    async def test_batch_update_wrong_tech(
        self, client, other_auth_header, job_en_cours
    ):
        """Batch update with wrong tech → 403."""
        resp = await client.put(
            f"/api/v1/jobs/{job_en_cours.id}/checklist/batch",
            json={"items": []},
            headers=other_auth_header,
        )
        assert resp.status_code == 403


class TestPhotosExtra:
    """Covers missing lines: photo delete by wrong tech, delete not found."""

    async def test_delete_photo_wrong_tech(
        self, client, other_auth_header, job_en_cours
    ):
        """Delete photo with wrong tech → 403."""
        resp = await client.delete(
            f"/api/v1/jobs/{job_en_cours.id}/photos/1",
            headers=other_auth_header,
        )
        assert resp.status_code == 403
