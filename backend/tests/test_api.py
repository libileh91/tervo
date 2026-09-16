"""
Tervo — API integration tests for Sprint 2.2.

Tests for photos, materials, report, and review endpoints.

Run:
    cd backend/
    .venv/bin/python -m pytest tests/test_api.py -v
    .venv/bin/python -m pytest tests/test_api.py -v --cov=app --cov-report=term-missing
"""

import io
import os
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest
from httpx import ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.core.database import get_db
from app.core.security import create_access_token
from app.main import app
from app.models import Base
from app.models.checklist_item import ChecklistItem
from app.models.client import Client
from app.models.job import Job, JobStatus
from app.models.job_photo import JobPhoto
from app.models.material import Material
from app.models.review import Review
from app.models.user import User

# ── Test database ────────────────────────────────────────

TEST_DB_URL = "sqlite+aiosqlite:///./test_tervo.db"
test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestSessionLocal = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)


async def _create_tables():
    """Create all tables in the test database."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def _drop_tables():
    """Drop all tables in the test database."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def _get_test_db():
    """FastAPI dependency override — returns test session."""
    async with TestSessionLocal() as session:
        yield session


@pytest.fixture
async def client():
    """Async HTTP client with test database."""
    await _create_tables()
    app.dependency_overrides[get_db] = _get_test_db
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
    await _drop_tables()


@pytest.fixture
async def db():
    """Direct test DB session for seeding data."""
    async with TestSessionLocal() as session:
        yield session


# ── Auth helpers ─────────────────────────────────────────


@pytest.fixture
async def tech_user(db: AsyncSession) -> User:
    """Create and return a technician user."""
    user = User(
        username="test_tech",
        email="tech@test.com",
        hashed_password="dummy",
        full_name="Test Tech",
        role="technician",
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.fixture
async def other_tech_user(db: AsyncSession) -> User:
    """Another technician user (not assigned to jobs, for 403 tests)."""
    user = User(
        username="other_tech",
        email="other@test.com",
        hashed_password="dummy",
        full_name="Other Tech",
        role="technician",
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.fixture
def other_auth_header(other_tech_user: User) -> dict:
    """Auth header for another technician (not assigned)."""
    token = create_access_token(user_id=other_tech_user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def token(tech_user: User) -> str:
    """JWT token for the test technician."""
    return create_access_token(user_id=tech_user.id)


@pytest.fixture
def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


TEST_PHOTO_PATH = Path(__file__).parent / "test_photo.jpg"


@pytest.fixture
def test_photo_bytes() -> bytes:
    """Load the test JPEG file."""
    with open(TEST_PHOTO_PATH, "rb") as f:
        return f.read()


# ── Data fixtures ────────────────────────────────────────


@pytest.fixture
async def client_fixture(db: AsyncSession) -> Client:
    """Create a test client."""
    c = Client(full_name="Test Client", phone="0100000000", address="1 rue Test")
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return c


@pytest.fixture
async def job_planifie(
    db: AsyncSession, tech_user: User, client_fixture: Client
) -> Job:
    """Create a planifié job."""
    j = Job(
        client_id=client_fixture.id,
        technician_id=tech_user.id,
        title="Test Job Planifié",
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
    """Create a job en_cours with checklist items."""
    j = Job(
        client_id=client_fixture.id,
        technician_id=tech_user.id,
        title="Test Job En Cours",
        status=JobStatus.EN_COURS,
        scheduled_date=date.today(),
        started_at=datetime.now(timezone.utc),
    )
    db.add(j)
    await db.commit()
    await db.refresh(j)

    # Seed checklist items (all checked)
    for i, (cat, label) in enumerate(
        [
            ("pre_intervention", "Check item A"),
            ("post_intervention", "Check item B"),
        ]
    ):
        item = ChecklistItem(
            job_id=j.id, category=cat, label=label, checked=True, position=i
        )
        db.add(item)
    await db.commit()

    return j


@pytest.fixture
async def job_termine(db: AsyncSession, tech_user: User, client_fixture: Client) -> Job:
    """Create a terminé job with photo, material, and review."""
    j = Job(
        client_id=client_fixture.id,
        technician_id=tech_user.id,
        title="Test Job Terminé",
        status=JobStatus.TERMINE,
        scheduled_date=date.today(),
        started_at=datetime.now(timezone.utc) - timedelta(hours=2),
        completed_at=datetime.now(timezone.utc),
    )
    db.add(j)
    await db.commit()
    await db.refresh(j)
    return j


# ═══════════════════════════════════════════════════════════
# PHOTOS
# ═══════════════════════════════════════════════════════════


class TestPhotos:
    """Tests pour INT-23 (upload) et INT-24 (delete)."""

    async def test_upload_photo_success(
        self, client, auth_header, job_en_cours, test_photo_bytes
    ):
        """Upload valide → 201."""
        files = {"file": ("test.jpg", io.BytesIO(test_photo_bytes), "image/jpeg")}
        resp = await client.post(
            f"/api/v1/jobs/{job_en_cours.id}/photos",
            data={"category": "avant"},
            files=files,
            headers=auth_header,
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["category"] == "avant"
        assert "file_url" in data
        assert "thumbnail_url" in data

    async def test_upload_photo_invalid_format(self, client, auth_header, job_en_cours):
        """Format non supporté → 400."""
        file_content = io.BytesIO(b"fake gif data")
        files = {"file": ("test.gif", file_content, "image/gif")}
        resp = await client.post(
            f"/api/v1/jobs/{job_en_cours.id}/photos",
            data={"category": "avant"},
            files=files,
            headers=auth_header,
        )
        assert resp.status_code == 400, resp.text

    async def test_upload_photo_no_auth(self, client, job_en_cours, test_photo_bytes):
        """Sans token → 401."""
        files = {"file": ("test.jpg", io.BytesIO(test_photo_bytes), "image/jpeg")}
        resp = await client.post(
            f"/api/v1/jobs/{job_en_cours.id}/photos",
            data={"category": "avant"},
            files=files,
        )
        assert resp.status_code == 401

    async def test_upload_photo_wrong_assignation(
        self, client, job_en_cours, other_auth_header, test_photo_bytes
    ):
        """Autre technicien → 403."""
        files = {"file": ("test.jpg", io.BytesIO(test_photo_bytes), "image/jpeg")}
        resp = await client.post(
            f"/api/v1/jobs/{job_en_cours.id}/photos",
            data={"category": "avant"},
            files=files,
            headers=other_auth_header,
        )
        assert resp.status_code == 403

    async def test_delete_photo(
        self, client, auth_header, job_en_cours, test_photo_bytes
    ):
        """Suppression → 204."""
        # Upload first
        files = {"file": ("test.jpg", io.BytesIO(test_photo_bytes), "image/jpeg")}
        upload_resp = await client.post(
            f"/api/v1/jobs/{job_en_cours.id}/photos",
            data={"category": "après"},
            files=files,
            headers=auth_header,
        )
        photo_id = upload_resp.json()["id"]

        # Delete
        resp = await client.delete(
            f"/api/v1/jobs/{job_en_cours.id}/photos/{photo_id}",
            headers=auth_header,
        )
        assert resp.status_code == 204

    async def test_delete_photo_not_found(self, client, auth_header, job_en_cours):
        """Photo inexistante → 404."""
        resp = await client.delete(
            f"/api/v1/jobs/{job_en_cours.id}/photos/99999",
            headers=auth_header,
        )
        assert resp.status_code == 404

    async def test_delete_photo_twice(
        self, client, auth_header, job_en_cours, test_photo_bytes
    ):
        """Double suppression → 404."""
        files = {"file": ("test.jpg", io.BytesIO(test_photo_bytes), "image/jpeg")}
        upload_resp = await client.post(
            f"/api/v1/jobs/{job_en_cours.id}/photos",
            data={"category": "après"},
            files=files,
            headers=auth_header,
        )
        photo_id = upload_resp.json()["id"]

        # First delete
        await client.delete(
            f"/api/v1/jobs/{job_en_cours.id}/photos/{photo_id}",
            headers=auth_header,
        )
        # Second delete
        resp = await client.delete(
            f"/api/v1/jobs/{job_en_cours.id}/photos/{photo_id}",
            headers=auth_header,
        )
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════
# MATÉRIAUX
# ═══════════════════════════════════════════════════════════


class TestMaterials:
    """Tests pour INT-26 (CRUD matériaux)."""

    async def test_create_material(self, client, auth_header, job_en_cours):
        """Ajout → 201."""
        resp = await client.post(
            f"/api/v1/jobs/{job_en_cours.id}/materials",
            json={"name": "Filtre HEPA", "quantity": "2"},
            headers=auth_header,
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["name"] == "Filtre HEPA"
        assert data["quantity"] == "2"

    async def test_list_materials(self, client, auth_header, job_en_cours):
        """Liste → 200."""
        # Add one
        await client.post(
            f"/api/v1/jobs/{job_en_cours.id}/materials",
            json={"name": "Vis", "quantity": "10"},
            headers=auth_header,
        )
        resp = await client.get(
            f"/api/v1/jobs/{job_en_cours.id}/materials",
            headers=auth_header,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    async def test_update_material(self, client, auth_header, job_en_cours):
        """Modification → 200."""
        created = await client.post(
            f"/api/v1/jobs/{job_en_cours.id}/materials",
            json={"name": "Câble", "quantity": "5m"},
            headers=auth_header,
        )
        mat_id = created.json()["id"]

        resp = await client.put(
            f"/api/v1/jobs/{job_en_cours.id}/materials/{mat_id}",
            json={"quantity": "10m"},
            headers=auth_header,
        )
        assert resp.status_code == 200
        assert resp.json()["quantity"] == "10m"

    async def test_delete_material(self, client, auth_header, job_en_cours):
        """Suppression → 204."""
        created = await client.post(
            f"/api/v1/jobs/{job_en_cours.id}/materials",
            json={"name": "Joint", "quantity": "1"},
            headers=auth_header,
        )
        mat_id = created.json()["id"]

        resp = await client.delete(
            f"/api/v1/jobs/{job_en_cours.id}/materials/{mat_id}",
            headers=auth_header,
        )
        assert resp.status_code == 204

    async def test_materials_no_auth(self, client, job_en_cours):
        """Sans auth → 401."""
        resp = await client.get(f"/api/v1/jobs/{job_en_cours.id}/materials")
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════
# RAPPORT
# ═══════════════════════════════════════════════════════════


class TestReport:
    """Tests pour INT-30 (download rapport)."""

    async def test_report_download_terminated(self, client, auth_header, job_termine):
        """Job terminé → 200 + PDF."""
        resp = await client.get(
            f"/api/v1/jobs/{job_termine.id}/report/download",
            headers=auth_header,
        )
        assert resp.status_code == 200, resp.text
        assert resp.headers["content-type"] == "application/pdf"
        assert "rapport-intervention" in resp.headers.get("content-disposition", "")
        assert len(resp.content) > 0

    async def test_report_download_not_terminated(
        self, client, auth_header, job_en_cours
    ):
        """Job non terminé → 400."""
        resp = await client.get(
            f"/api/v1/jobs/{job_en_cours.id}/report/download",
            headers=auth_header,
        )
        assert resp.status_code == 400
        assert "terminé" in resp.json()["detail"]

    async def test_report_download_not_found(self, client, auth_header):
        """Job inexistant → 404."""
        resp = await client.get(
            "/api/v1/jobs/99999/report/download",
            headers=auth_header,
        )
        assert resp.status_code == 404

    async def test_report_download_no_auth(self, client, job_termine):
        """Sans auth → 401."""
        resp = await client.get(f"/api/v1/jobs/{job_termine.id}/report/download")
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════
# AVIS PUBLIC
# ═══════════════════════════════════════════════════════════


class TestReview:
    """Tests pour INT-32 (GET review) et INT-33 (POST submit)."""

    @pytest.fixture
    async def review_valide(self, db: AsyncSession, job_termine: Job) -> Review:
        """Create a valid, unsubmitted review."""
        r = Review(
            job_id=job_termine.id,
            rating=5,
            share_token=uuid.uuid4().hex,
            share_token_expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        )
        db.add(r)
        await db.commit()
        await db.refresh(r)
        return r

    @pytest.fixture
    async def review_expired(self, db: AsyncSession, job_planifie: Job) -> Review:
        """Create an expired review."""
        r = Review(
            job_id=job_planifie.id,
            rating=5,
            share_token=uuid.uuid4().hex,
            share_token_expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        db.add(r)
        await db.commit()
        await db.refresh(r)
        return r

    async def test_get_review_valid(self, client, review_valide):
        """Token valide → 200 + infos job."""
        resp = await client.get(f"/api/v1/review/{review_valide.share_token}")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "job" in data
        assert "technician" in data
        assert data["already_reviewed"] is False

    async def test_get_review_invalid_token(self, client):
        """Token invalide → 404."""
        resp = await client.get("/api/v1/review/invalid_token_xxx")
        assert resp.status_code == 404
        assert "invalide" in resp.json()["detail"]

    async def test_get_review_expired(self, client, review_expired):
        """Token expiré → 404."""
        resp = await client.get(f"/api/v1/review/{review_expired.share_token}")
        assert resp.status_code == 404
        assert "invalide" in resp.json()["detail"]

    async def test_get_review_public_no_auth(self, client, review_valide):
        """Sans auth → 200 (public)."""
        resp = await client.get(f"/api/v1/review/{review_valide.share_token}")
        assert resp.status_code == 200

    async def test_submit_review_success(self, client, review_valide):
        """Soumission valide → 200."""
        resp = await client.post(
            f"/api/v1/review/{review_valide.share_token}/submit",
            json={"rating": 4, "comment": "Très bien", "reviewer_name": "Client"},
        )
        assert resp.status_code == 200, resp.text
        assert "Merci" in resp.json()["message"]

    async def test_submit_review_double(self, client, review_valide):
        """Double soumission → 400."""
        await client.post(
            f"/api/v1/review/{review_valide.share_token}/submit",
            json={"rating": 4},
        )
        resp = await client.post(
            f"/api/v1/review/{review_valide.share_token}/submit",
            json={"rating": 5},
        )
        assert resp.status_code == 400
        assert "déjà" in resp.json()["detail"]

    async def test_submit_review_invalid_token(self, client):
        """Token invalide → 404."""
        resp = await client.post(
            "/api/v1/review/invalid_token/submit",
            json={"rating": 4},
        )
        assert resp.status_code == 404

    async def test_submit_review_rating_out_of_range(self, client, review_valide):
        """Rating hors limite → 422."""
        resp = await client.post(
            f"/api/v1/review/{review_valide.share_token}/submit",
            json={"rating": 0},
        )
        assert resp.status_code == 422

    async def test_submit_review_public_no_auth(self, client, review_valide):
        """Sans auth → 200 (public)."""
        resp = await client.post(
            f"/api/v1/review/{review_valide.share_token}/submit",
            json={"rating": 3},
        )
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════
# INTÉGRATION
# ═══════════════════════════════════════════════════════════


class TestIntegration:
    """Tests d'intégration : complete_job → création review."""

    async def test_complete_job_creates_review(self, client, auth_header, job_en_cours):
        """Compléter un job crée un Review avec share_token."""
        resp = await client.put(
            f"/api/v1/jobs/{job_en_cours.id}/complete",
            json={"observations": "Test"},
            headers=auth_header,
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["status"] == "terminé"
        assert data["review_share_token"] is not None
        assert data["review_share_url"] is not None
        assert data["report_url"] is not None
        assert "/review/" in data["review_share_url"]

        # Vérifier que le review existe en base
        async with TestSessionLocal() as db:
            result = await db.execute(
                select(Review).where(Review.job_id == job_en_cours.id)
            )
            review = result.scalar_one_or_none()
            assert review is not None
            assert review.share_token == data["review_share_token"]

    async def test_complete_job_not_en_cours(self, client, auth_header, job_planifie):
        """Job planifié → 400."""
        resp = await client.put(
            f"/api/v1/jobs/{job_planifie.id}/complete",
            json={},
            headers=auth_header,
        )
        assert resp.status_code == 400

    async def test_complete_job_wrong_technician(
        self, client, job_en_cours, other_auth_header
    ):
        """Mauvais technicien → 403."""
        resp = await client.put(
            f"/api/v1/jobs/{job_en_cours.id}/complete",
            json={},
            headers=other_auth_header,
        )
        assert resp.status_code == 403
