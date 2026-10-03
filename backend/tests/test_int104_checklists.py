"""INT-104 API and transaction regression tests, using isolated SQLite only."""

import asyncio
import os
from datetime import date
from uuid import uuid4

import httpx
import pytest
from fastapi import HTTPException
from sqlalchemy import event, func, select, text
from sqlalchemy.sql.selectable import Select
from sqlalchemy.sql.dml import Update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.base import Base
from app.core.database import get_db
from app.core.security import create_access_token
from app.main import app
from app.modules.customers.models import Client, Site
from app.modules.identity.models import Role, User
from app.modules.interventions.models.checklist import InterventionChecklist
from app.modules.interventions.models.checklist_item import ChecklistItem
from app.modules.interventions.models.intervention import Intervention, InterventionStatus
from app.modules.interventions.repositories.intervention import InterventionRepository
from app.modules.interventions.schemas.intervention import InterventionCreate
from app.modules.interventions.schemas.checklist import ChecklistTemplateUpdate
from app.modules.interventions.services.checklist import ChecklistService
from app.modules.interventions.services.intervention import InterventionService

PREFIX = "/api/v1"
TEMPLATE = {
    "name": "Contrôle chaudière", "intervention_type": "Entretien chaudière",
    "items": [
        {"label": "Contrôler pression", "category": "pre_intervention", "position": 0},
        {"label": "Tester fonctionnement", "category": "post_intervention", "position": 1},
    ],
}


@pytest.fixture
async def context(tmp_path):
    url = os.environ.get("TERVO_CHECKLIST_TEST_DATABASE_URL")
    schema = f"int104_{uuid4().hex}" if url else None
    bootstrap_engine = None
    if schema:
        # The URL must point to a disposable test server, never an existing
        # application database. Even there, use a fresh private schema.
        bootstrap_engine = create_async_engine(url)
        async with bootstrap_engine.begin() as connection:
            await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        engine = create_async_engine(url, connect_args={"server_settings": {"search_path": schema}})
    else:
        engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'int104.sqlite'}")
        @event.listens_for(engine.sync_engine, "connect")
        def enable_foreign_keys(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with sessions() as db:
        users = [
            User(username=name, email=f"{name}@test.invalid", hashed_password="unused",
                 role=role, is_active=True)
            for name, role in (("admin", Role.ADMIN), ("tech", Role.TECHNICIAN), ("other", Role.TECHNICIAN))
        ]
        customer = Client(full_name="INT104", phone="0600000000", address="Test")
        db.add_all([*users, customer])
        await db.flush()
        site = Site(client_id=customer.id, name="Test", address="Test")
        db.add(site)
        await db.commit()
        headers = {user.username: {"Authorization": f"Bearer {create_access_token(user_id=user.id)}"} for user in users}
        site_id = site.id
        tech_id = users[1].id

    async def override_db():
        async with sessions() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            yield client, sessions, headers, site_id, tech_id
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()
        if bootstrap_engine:
            async with bootstrap_engine.begin() as connection:
                await connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
            await bootstrap_engine.dispose()


async def create_intervention(context, template_id=None):
    client, _, headers, site_id, _ = context
    body = {"site_id": site_id, "title": "Contrôle", "scheduled_date": str(date.today())}
    if template_id is not None:
        body["checklist_template_id"] = template_id
    response = await client.post(f"{PREFIX}/interventions", json=body, headers=headers["tech"])
    assert response.status_code == 201, response.text
    return response.json()


async def create_template(context):
    client, _, headers, _, _ = context
    response = await client.post(f"{PREFIX}/checklist-templates", json=TEMPLATE, headers=headers["admin"])
    assert response.status_code == 201, response.text
    return response.json()


async def test_templates_permissions_and_snapshot_history(context):
    client, _, headers, _, _ = context
    assert (await client.get(f"{PREFIX}/checklist-templates")).status_code in (401, 403)
    assert (await client.get(f"{PREFIX}/checklist-templates", headers=headers["tech"])).status_code == 200
    assert (await client.post(f"{PREFIX}/checklist-templates", json=TEMPLATE, headers=headers["tech"])).status_code == 403
    template = await create_template(context)
    first = await create_intervention(context, template["id"])
    snapshot = (await client.get(f"{PREFIX}/interventions/{first['id']}/checklist", headers=headers["tech"])).json()
    assert snapshot["template_version"] == 1
    assert snapshot["template_name"] == TEMPLATE["name"]
    assert len(snapshot["items"]) == 2
    assert all(item["result"] is None and item["completed_at"] is None for item in snapshot["items"])
    assert first["checklist_items"] == snapshot["items"]
    changed = {"name": "Nouveau contrôle", "items": [{"label": "Nouveau", "category": "pre_intervention", "position": 2}]}
    assert (await client.patch(f"{PREFIX}/checklist-templates/{template['id']}", json=changed, headers=headers["tech"])).status_code == 403
    response = await client.patch(f"{PREFIX}/checklist-templates/{template['id']}", json=changed, headers=headers["admin"])
    assert response.status_code == 200, response.text
    assert response.json()["version"] == 2
    historical = (await client.get(f"{PREFIX}/interventions/{first['id']}/checklist", headers=headers["other"])).json()
    assert historical == snapshot
    second = await create_intervention(context, template["id"])
    current = (await client.get(f"{PREFIX}/interventions/{second['id']}/checklist", headers=headers["tech"])).json()
    assert current["template_version"] == 2
    assert current["items"][0]["label"] == "Nouveau"


async def test_default_result_comment_permissions_and_locked_status(context):
    client, sessions, headers, _, _ = context
    intervention = await create_intervention(context)
    response = await client.get(f"{PREFIX}/interventions/{intervention['id']}/checklist", headers=headers["tech"])
    snapshot = response.json()
    assert snapshot["template_id"] is None
    assert len(snapshot["items"]) == 5
    item_id = snapshot["items"][0]["id"]
    path = f"{PREFIX}/checklist-items/{item_id}"
    for user in ("admin", "other"):
        assert (await client.patch(path, json={"result": "OK"}, headers=headers[user])).status_code == 403
    for body in ({"result": ""}, {"result": "   "}, {"result": "a" * 101}, {"label": "Modified"}, {"checked": True}, {"completed_at": None}):
        assert (await client.patch(path, json=body, headers=headers["tech"])).status_code == 422
    done = await client.patch(path, json={"result": "À remplacer", "comment": "Pression faible"}, headers=headers["tech"])
    assert done.status_code == 200, done.text
    assert done.json()["completed_at"] is not None
    timestamp = done.json()["completed_at"]
    comment = await client.patch(path, json={"comment": None}, headers=headers["tech"])
    assert comment.json()["result"] == "À remplacer"
    assert comment.json()["completed_at"] == timestamp
    repeated = await client.patch(path, json={"result": "À remplacer", "comment": "Commentaire corrigé"}, headers=headers["tech"])
    assert repeated.json()["completed_at"] == timestamp
    reset = await client.patch(path, json={"result": None}, headers=headers["tech"])
    assert reset.json()["completed_at"] is None
    async with sessions() as db:
        intervention_orm = await db.get(Intervention, intervention["id"])
        intervention_orm.status = InterventionStatus.CANCELLED
        await db.commit()
    assert (await client.patch(path, json={"result": "OK"}, headers=headers["tech"])).status_code == 422
    assert (await client.patch(f"{PREFIX}/checklist-items/99999", json={"result": "OK"}, headers=headers["tech"])).status_code == 404
    assert (await client.post(f"{PREFIX}/interventions/{intervention['id']}/checklist", json={"label": "Add"}, headers=headers["tech"])).status_code == 405
    assert (await client.put(f"{PREFIX}/interventions/{intervention['id']}/checklist/{item_id}", json={"checked": True}, headers=headers["tech"])).status_code in (404, 405)


@pytest.mark.parametrize("change", [
    {"items": []}, {"name": " "}, {"intervention_type": " "}, {"version": 0},
    {"version": True}, {"active": "yes"},
    {"items": [{"label": " ", "category": "pre_intervention", "position": 0}]},
    {"items": [{"label": "Test", "category": "other", "position": 0}]},
    {"items": [{"label": "Test", "category": "pre_intervention", "position": -1}]},
    {"items": [{"label": "Test", "category": "pre_intervention", "position": True}]},
])
async def test_template_creation_validation(context, change):
    client, _, headers, _, _ = context
    assert (await client.post(f"{PREFIX}/checklist-templates", json={**TEMPLATE, **change}, headers=headers["admin"])).status_code == 422


async def test_template_selection_and_creation_rollback(context, monkeypatch):
    client, sessions, headers, site_id, tech_id = context
    body = {"site_id": site_id, "title": "Rollback", "scheduled_date": str(date.today())}
    assert (await client.post(f"{PREFIX}/interventions", json={**body, "checklist_template_id": 0}, headers=headers["tech"])).status_code == 422
    assert (await client.post(f"{PREFIX}/interventions", json={**body, "checklist_template_id": 99999}, headers=headers["tech"])).status_code == 404
    template = await create_template(context)
    await client.patch(f"{PREFIX}/checklist-templates/{template['id']}", json={"active": False}, headers=headers["admin"])
    assert (await client.post(f"{PREFIX}/interventions", json={**body, "checklist_template_id": template["id"]}, headers=headers["tech"])).status_code == 422

    original = ChecklistService.create_snapshot
    async def fail_after_flush(self, *args):
        await original(self, *args)
        raise RuntimeError("snapshot failure after items flushed")
    monkeypatch.setattr(ChecklistService, "create_snapshot", fail_after_flush)
    async with sessions() as db:
        user = await db.get(User, tech_id)
        with pytest.raises(RuntimeError, match="snapshot failure"):
            await InterventionService(db).create_intervention(InterventionCreate(**body), user)
    async with sessions() as db:
        for model in (Intervention, InterventionChecklist, ChecklistItem):
            assert await db.scalar(select(func.count()).select_from(model)) == 0


async def test_historical_empty_snapshot_get_is_read_only(context):
    client, sessions, headers, site_id, tech_id = context
    async with sessions() as db:
        intervention = Intervention(site_id=site_id, technician_id=tech_id, title="Historique", scheduled_date=date.today())
        db.add(intervention)
        await db.flush()
        db.add(InterventionChecklist(intervention_id=intervention.id, template_name="Checklist historique", template_version=1, items=[]))
        await db.commit()
        intervention_id = intervention.id
    for _ in range(2):
        response = await client.get(f"{PREFIX}/interventions/{intervention_id}/checklist", headers=headers["tech"])
        assert response.status_code == 200
        assert response.json()["items"] == []
    async with sessions() as db:
        assert await db.scalar(select(func.count()).select_from(ChecklistItem)) == 0


async def test_get_missing_snapshot_never_creates_controls(context):
    client, sessions, headers, site_id, tech_id = context
    async with sessions() as db:
        intervention = Intervention(site_id=site_id, technician_id=tech_id, title="No snapshot", scheduled_date=date.today())
        db.add(intervention)
        await db.commit()
        intervention_id = intervention.id
    response = await client.get(f"{PREFIX}/interventions/{intervention_id}/checklist", headers=headers["tech"])
    assert response.status_code == 404
    async with sessions() as db:
        for model in (InterventionChecklist, ChecklistItem):
            assert await db.scalar(select(func.count()).select_from(model)) == 0


async def test_template_patch_validation_and_snapshot_delete_cascade(context):
    client, sessions, headers, _, _ = context
    template = await create_template(context)
    for body in ({}, {"name": None}, {"items": None}, {"items": []}, {"active": None},
                 {"version": 10}, {"name": " "}, {"intervention_type": "x" * 101}):
        response = await client.patch(f"{PREFIX}/checklist-templates/{template['id']}", json=body, headers=headers["admin"])
        assert response.status_code == 422, response.text
    current = (await client.get(f"{PREFIX}/checklist-templates", headers=headers["admin"])).json()
    assert current[0]["version"] == 1
    intervention = await create_intervention(context, template["id"])
    async with sessions() as db:
        await InterventionService(db).delete_intervention(intervention["id"])
    async with sessions() as db:
        for model in (InterventionChecklist, ChecklistItem):
            assert await db.scalar(select(func.count()).select_from(model)) == 0


async def test_completion_accepts_any_nonnull_result(context):
    _, sessions, _, _, _ = context
    intervention = await create_intervention(context)
    async with sessions() as db:
        service = ChecklistService(db)
        assert not (await service.validate_all_checked(intervention["id"]))["is_valid"]
        for item in await service.get_items(intervention["id"]):
            item.result = "Non conforme — action requise"
        await db.commit()
        assert (await service.validate_all_checked(intervention["id"]))["is_valid"]


async def test_concurrent_template_updates_are_atomic(context):
    """Force both writers to read the same version before compare-and-swap."""
    client, sessions, headers, _, _ = context
    template = await create_template(context)
    barrier = asyncio.Barrier(2)

    async def writer(name):
        async with sessions() as db:
            execute = db.execute

            async def synchronized_execute(statement, *args, **kwargs):
                result = await execute(statement, *args, **kwargs)
                if isinstance(statement, Select):
                    await barrier.wait()
                return result

            db.execute = synchronized_execute
            try:
                result = await ChecklistService(db).update_template(
                    template["id"], ChecklistTemplateUpdate(name=name),
                )
                return result.name
            except HTTPException as error:
                assert error.status_code == 409
                return None

    results = await asyncio.wait_for(asyncio.gather(writer("Version A"), writer("Version B")), timeout=15)
    assert sum(result is not None for result in results) == 1
    current = (await client.get(f"{PREFIX}/checklist-templates", headers=headers["tech"])).json()[0]
    assert current["version"] == 2
    assert current["name"] == next(result for result in results if result is not None)


@pytest.mark.skipif(not os.environ.get("TERVO_CHECKLIST_TEST_DATABASE_URL"), reason="requires disposable PostgreSQL test server")
async def test_snapshot_creation_holds_coherent_template_version(context, monkeypatch):
    """A concurrent PATCH waits until the complete old snapshot has committed."""
    client, sessions, headers, site_id, tech_id = context
    template = await create_template(context)
    snapshot_flushed = asyncio.Event()
    patch_started = asyncio.Event()
    release_snapshot = asyncio.Event()
    original = ChecklistService.create_snapshot

    async def pause_snapshot(self, *args):
        snapshot = await original(self, *args)
        snapshot_flushed.set()
        await release_snapshot.wait()
        return snapshot

    monkeypatch.setattr(ChecklistService, "create_snapshot", pause_snapshot)

    async def create():
        async with sessions() as db:
            user = await db.get(User, tech_id)
            return await InterventionService(db).create_intervention(
                InterventionCreate(site_id=site_id, title="Concurrent snapshot",
                                   scheduled_date=date.today(), checklist_template_id=template["id"]),
                user,
            )

    async def patch():
        async with sessions() as db:
            execute = db.execute

            async def signal_update(statement, *args, **kwargs):
                if isinstance(statement, Update):
                    patch_started.set()
                return await execute(statement, *args, **kwargs)

            db.execute = signal_update
            return await ChecklistService(db).update_template(
                template["id"], ChecklistTemplateUpdate(
                    name="Next version",
                    items=[{"label": "New control", "category": "post_intervention", "position": 0}],
                ),
            )

    create_task = asyncio.create_task(create())
    patch_task = None
    try:
        await asyncio.wait_for(snapshot_flushed.wait(), 10)
        patch_task = asyncio.create_task(patch())
        await asyncio.wait_for(patch_started.wait(), 10)
        await asyncio.sleep(0.05)
        assert not patch_task.done(), "PATCH must wait for the snapshot's template lock"
        release_snapshot.set()
        created, patched = await asyncio.wait_for(asyncio.gather(create_task, patch_task), 10)
        assert patched.version == 2
        snapshot = (await client.get(f"{PREFIX}/interventions/{created.id}/checklist", headers=headers["tech"])).json()
        assert snapshot["template_name"] == TEMPLATE["name"]
        assert snapshot["template_version"] == 1
        assert [item["label"] for item in snapshot["items"]] == [item["label"] for item in TEMPLATE["items"]]
    finally:
        release_snapshot.set()
        for task in (create_task, patch_task):
            if task and not task.done():
                task.cancel()
        await asyncio.gather(*(task for task in (create_task, patch_task) if task), return_exceptions=True)


@pytest.mark.skipif(not os.environ.get("TERVO_CHECKLIST_TEST_DATABASE_URL"), reason="requires disposable PostgreSQL test server")
@pytest.mark.parametrize("transition", ["complete", "cancel"])
@pytest.mark.parametrize("first", ["patch", "transition"])
async def test_item_patch_and_terminal_transition_share_intervention_lock(context, monkeypatch, transition, first):
    """Serialize both orderings, including a PATCH that read stale ORM state."""
    client, sessions, headers, _, _ = context
    intervention = await create_intervention(context)
    intervention_id = intervention["id"]
    item_id = intervention["checklist_items"][0]["id"]
    async with sessions() as db:
        current = await db.get(Intervention, intervention_id)
        current.status = InterventionStatus.IN_PROGRESS if transition == "complete" else InterventionStatus.PLANNED
        for item in await ChecklistService(db).get_items(intervention_id):
            item.result = "OK"
        await db.commit()

    locked = asyncio.Event()
    second_started = asyncio.Event()
    release_first = asyncio.Event()
    original = InterventionRepository.get_by_id

    async def hold_first_lock(self, key, *, for_update=False):
        name = asyncio.current_task().get_name()
        if for_update and name == "second-writer":
            second_started.set()
        result = await original(self, key, for_update=for_update)
        if for_update and name == "first-writer":
            locked.set()
            await release_first.wait()
        return result

    monkeypatch.setattr(InterventionRepository, "get_by_id", hold_first_lock)

    async def patch():
        return await client.patch(f"{PREFIX}/checklist-items/{item_id}", json={"result": None}, headers=headers["tech"])

    async def change_status():
        body = {"result": "RESOLVED"} if transition == "complete" else {}
        return await client.put(f"{PREFIX}/interventions/{intervention_id}/{transition}", json=body, headers=headers["tech"])

    actions = {"patch": patch, "transition": change_status}
    second = "transition" if first == "patch" else "patch"
    first_task = asyncio.create_task(actions[first](), name="first-writer")
    second_task = None
    try:
        await asyncio.wait_for(locked.wait(), 10)
        second_task = asyncio.create_task(actions[second](), name="second-writer")
        await asyncio.wait_for(second_started.wait(), 10)
        await asyncio.sleep(0.05)
        assert not second_task.done(), "The second writer must wait for the intervention lock"
        release_first.set()
        first_response, second_response = await asyncio.wait_for(asyncio.gather(first_task, second_task), 10)
        assert first_response.status_code == 200, first_response.text
        if first == "transition":
            assert second_response.status_code == 422, second_response.text
        else:
            assert second_response.status_code == (400 if transition == "complete" else 200), second_response.text
        async with sessions() as db:
            item = await db.get(ChecklistItem, item_id)
            current = await db.get(Intervention, intervention_id)
            if first == "transition":
                assert item.result == "OK"
                assert current.status == (InterventionStatus.COMPLETED if transition == "complete" else InterventionStatus.CANCELLED)
            else:
                assert item.result is None
                assert current.status == (InterventionStatus.IN_PROGRESS if transition == "complete" else InterventionStatus.CANCELLED)
    finally:
        release_first.set()
        for task in (first_task, second_task):
            if task and not task.done():
                task.cancel()
        await asyncio.gather(*(task for task in (first_task, second_task) if task), return_exceptions=True)
