"""INT-106 completion contracts: real JWT, disposable SQLite/PG database."""
import asyncio
import os
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import event, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.core.base import Base
from app.core.database import get_db
from app.core.security import create_access_token
from app.main import app
from app.modules.customers.models import Client, Site
from app.modules.identity.models import Role, User
from app.modules.interventions.models.intervention import Intervention, InterventionStatus
from app.modules.interventions.models.checklist_item import ChecklistItem
from app.modules.interventions.models.review import Review
from app.modules.interventions.repositories.review import ReviewRepository

RESULTS = ("RESOLVED", "PARTIALLY_RESOLVED", "UNRESOLVED", "PART_NEEDED", "QUOTE_NEEDED", "RESCHEDULE")


@pytest.fixture
async def completion(tmp_path, monkeypatch):
    url = os.environ.get("TERVO_RESULT_TEST_DATABASE_URL")
    schema = "result_test_" + uuid4().hex
    admin = None
    if url:
        assert url.startswith("postgresql+asyncpg://")
        admin = create_async_engine(url)
        async with admin.begin() as db:
            await db.execute(text(f'CREATE SCHEMA "{schema}"'))
        engine = create_async_engine(url, connect_args={"server_settings": {"search_path": schema}})
    else:
        engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'result.db'}")
        @event.listens_for(engine.sync_engine, "connect")
        def foreign_keys(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path / "uploads"))
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as db:
        await db.run_sync(Base.metadata.create_all)
    async with sessions() as db:
        users = [User(username=f"result-{i}", email=f"result-{i}@test.fr",
                      role=Role.TECHNICIAN, **{"hashed_" + "password": "unused"}) for i in range(2)]
        owner = Client(full_name="Result owner", phone="0102030405", address="Paris")
        db.add_all([*users, owner])
        await db.flush()
        site = Site(client_id=owner.id, name="Result", address="Paris")
        db.add(site)
        await db.commit()
        site_id = site.id
        tokens = [{"Authorization": "Bearer " + create_access_token(user.id)} for user in users]
    async def database():
        async with sessions() as db:
            yield db
    previous = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = database
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test",
                                     headers=tokens[0]) as client:
            response = await client.post("/api/v1/interventions", json={
                "site_id": site_id, "title": "Outcome", "scheduled_date": "2026-09-28",
            })
            assert response.status_code == 201, response.text
            parent = "/api/v1/interventions/" + str(response.json()["id"])
            yield client, sessions, parent, tokens[1], site_id
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
        await engine.dispose()
        if admin:
            async with admin.begin() as db:
                await db.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
            await admin.dispose()


async def ready(completion, *, empty=False):
    client, sessions, parent, _, _ = completion
    assert (await client.put(parent + "/start")).status_code == 200
    async with sessions() as db:
        intervention = await db.get(Intervention, int(parent.rsplit("/", 1)[1]))
        intervention.observations = "Original notes"
        intervention.started_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=12)
        if empty:
            for item in (await db.execute(select(ChecklistItem))).scalars():
                await db.delete(item)
        else:
            await db.execute(update(ChecklistItem).values(result="DONE"))
        await db.commit()


async def stored(completion):
    _, sessions, parent, _, _ = completion
    async with sessions() as db:
        intervention = await db.get(Intervention, int(parent.rsplit("/", 1)[1]))
        reviews = (await db.execute(select(Review))).scalars().all()
        return (intervention.status, intervention.result, intervention.observations,
                intervention.completed_at, [(r.id, r.share_token) for r in reviews])


@pytest.mark.parametrize("result", RESULTS)
async def test_all_results_atomic_detail_list_history_repeat(completion, result):
    client, _, parent, _, site_id = completion
    await ready(completion)
    response = await client.put(parent + "/complete", json={"result": result, "observations": "Explicit"})
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["result"] == result and data["status"] == "COMPLETED"
    assert data["duration_minutes"] >= 12
    assert data["review_share_url"] == "/review/" + data["review_share_token"]
    before = await stored(completion)
    assert before[:3] == (InterventionStatus.COMPLETED, result, "Explicit")
    assert len(before[4]) == 1 and before[4][0][1] == data["review_share_token"]
    assert (await client.get(parent)).json()["result"] == result
    assert (await client.get("/api/v1/interventions")).json()["items"][0]["result"] == result
    history = await client.get(f"/api/v1/sites/{site_id}/interventions")
    assert history.status_code == 200, history.text
    assert history.json()["items"][0]["result"] == result
    assert (await client.put(parent + "/complete", json={"result": "RESCHEDULE", "observations": "Overwrite"})).status_code == 400
    assert await stored(completion) == before


@pytest.mark.parametrize("body", [{}, {"result": None}, {"result": ""}, {"result": " "},
                                  {"result": "resolved"}, {"result": "INVALID"},
                                  {"result": "RESOLVED", "status": "COMPLETED"}])
async def test_invalid_completion_422_unchanged(completion, body):
    client, _, parent, _, _ = completion
    await ready(completion)
    before = await stored(completion)
    assert (await client.put(parent + "/complete", json=body)).status_code == 422
    assert await stored(completion) == before


@pytest.mark.parametrize("result", [None, "RESOLVED"])
async def test_generic_crud_cannot_set_result(completion, result):
    client, _, parent, _, site_id = completion
    assert (await client.post("/api/v1/interventions", json={
        "site_id": site_id, "title": "Bypass", "scheduled_date": "2026-09-28", "result": result,
    })).status_code == 422
    assert (await client.put(parent, json={"result": result})).status_code == 422
    assert (await client.get(parent)).json()["result"] is None


async def test_historical_completed_unknown_and_unknown_create_fields_ignored(completion):
    client, sessions, parent, _, site_id = completion
    async with sessions() as db:
        intervention = await db.get(Intervention, int(parent.rsplit("/", 1)[1]))
        intervention.status = InterventionStatus.COMPLETED
        await db.commit()
    assert (await client.get(parent)).json()["result"] is None
    assert (await client.get("/api/v1/interventions")).json()["items"][0]["result"] is None
    assert (await client.get(f"/api/v1/sites/{site_id}/interventions")).json()["items"][0]["result"] is None
    response = await client.post("/api/v1/interventions", json={
        "site_id": site_id, "title": "Import compatible", "scheduled_date": "2026-09-28",
        "extract": "legacy", "status": "COMPLETED",
    })
    assert response.status_code == 201, response.text
    assert response.json()["status"] == "PLANNED" and response.json()["result"] is None


async def test_cancelled_state_rejected(completion):
    client, _, parent, _, _ = completion
    assert (await client.put(parent + "/cancel")).status_code == 200
    before = await stored(completion)
    assert (await client.put(parent + "/complete", json={"result": "RESOLVED"})).status_code == 400
    assert await stored(completion) == before


async def test_explicit_empty_observations_replaces_existing(completion):
    client, _, parent, _, _ = completion
    await ready(completion)
    response = await client.put(parent + "/complete", json={"result": "UNRESOLVED", "observations": ""})
    assert response.status_code == 200, response.text
    assert (await stored(completion))[2] == ""


@pytest.mark.parametrize("body", [{"result": "PART_NEEDED"}, {"result": "PART_NEEDED", "observations": None}])
async def test_omitted_null_observations_preserved_empty_history_allowed(completion, body):
    client, _, parent, _, _ = completion
    await ready(completion, empty=True)
    assert (await client.put(parent + "/complete", json=body)).status_code == 200
    assert (await stored(completion))[:3] == (InterventionStatus.COMPLETED, "PART_NEEDED", "Original notes")


async def test_state_assignment_checklist_preconditions(completion):
    client, _, parent, foreign, _ = completion
    before = await stored(completion)
    assert (await client.put(parent + "/complete", json={"result": "RESOLVED"})).status_code == 400
    assert await stored(completion) == before
    assert (await client.put(parent + "/start")).status_code == 200
    before = await stored(completion)
    assert (await client.put(parent + "/complete", json={"result": "RESOLVED"}, headers=foreign)).status_code == 403
    assert (await client.put(parent + "/complete", json={"result": "RESOLVED"})).status_code == 400
    assert await stored(completion) == before


async def test_failure_after_review_flush_rolls_back_everything(completion):
    client, _, parent, _, _ = completion
    await ready(completion)
    before = await stored(completion)
    original = ReviewRepository.create
    async def fail_after_flush(self, data, *, commit=True):
        review = await original(self, data, commit=commit)
        assert review.id is not None and commit is False
        raise RuntimeError("after review flush")
    with patch.object(ReviewRepository, "create", fail_after_flush):
        with pytest.raises(RuntimeError, match="after review flush"):
            await client.put(parent + "/complete", json={"result": "QUOTE_NEEDED", "observations": "Changed"})
    assert await stored(completion) == before


async def test_response_validation_failure_rolls_back(completion):
    client, _, parent, _, _ = completion
    await ready(completion)
    before = await stored(completion)
    with patch("app.modules.interventions.services.intervention.InterventionCompleteResponse",
               side_effect=RuntimeError("response validation")):
        with pytest.raises(RuntimeError, match="response validation"):
            await client.put(parent + "/complete", json={"result": "RESOLVED"})
    assert await stored(completion) == before


async def test_commit_failure_rolls_back_outcome_observations_and_review(completion):
    client, _, parent, _, _ = completion
    await ready(completion)
    before = await stored(completion)
    with patch.object(AsyncSession, "commit", side_effect=RuntimeError("completion commit failure")):
        with pytest.raises(RuntimeError, match="completion commit failure"):
            await client.put(parent + "/complete", json={"result": "PART_NEEDED", "observations": "Changed"})
    # A new session sees neither partial completion nor a persisted review.
    assert await stored(completion) == before


async def test_postgresql_concurrent_completions_one_review(completion):
    if not os.environ.get("TERVO_RESULT_TEST_DATABASE_URL"):
        pytest.skip("PostgreSQL row-lock test requires TERVO_RESULT_TEST_DATABASE_URL")
    client, _, parent, _, _ = completion
    await ready(completion)
    responses = await asyncio.gather(*[
        client.put(parent + "/complete", json={"result": result}) for result in ("RESOLVED", "PART_NEEDED")
    ])
    assert sorted(response.status_code for response in responses) == [200, 400]
    state = await stored(completion)
    assert len(state[4]) == 1
    assert state[1] == next(response.json()["result"] for response in responses if response.status_code == 200)
