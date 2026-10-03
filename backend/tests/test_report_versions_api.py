"""INT-107: one API recipe on a disposable database, not a mock-only unit suite."""
from datetime import date
from hashlib import sha256
from uuid import uuid4
from unittest.mock import patch
import os

import httpx
import pytest
from sqlalchemy import event, func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.base import Base
from app.core.database import get_db
from app.core.security import create_access_token
from app.main import app
from app.modules.customers.models import Client, Site
from app.modules.identity.models import Role, User
from app.modules.interventions.models.intervention import Intervention, InterventionStatus
from app.modules.reports.models import Report, ReportVersion
from app.modules.reports.renderer import ReportExporter


@pytest.fixture
async def context(tmp_path):
    url = os.environ.get("TERVO_REPORT_TEST_DATABASE_URL")
    admin = None
    if url:
        assert url.startswith("postgresql+asyncpg://"), "Only a disposable test server"
        schema = "report_test_" + uuid4().hex
        admin = create_async_engine(url)
        async with admin.begin() as conn:
            await conn.execute(text(f'CREATE SCHEMA "{schema}"'))
        engine = create_async_engine(url, connect_args={"server_settings": {"search_path": schema}})
    else:
        engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'reports.db'}")
        @event.listens_for(engine.sync_engine, "connect")
        def foreign_keys(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with sessions() as db:
        users = [User(username=name, email=f"{name}@test.invalid", full_name=name, role=role,
                      hashed_password="unused") for name, role in
                 (("report-tech", Role.TECHNICIAN), ("report-other", Role.TECHNICIAN),
                  ("report-admin", Role.ADMIN))]
        client = Client(full_name="Report fixture", phone="0000000000", address="Test")
        db.add_all([*users, client])
        await db.flush()
        site = Site(client_id=client.id, name="Report site", address="Test")
        db.add(site)
        await db.flush()
        interventions = [
            Intervention(site_id=site.id, technician_id=users[0].id,
                         title=title, scheduled_date=date.today(), status=status,
                         result="PART_NEEDED" if status == InterventionStatus.COMPLETED else None,
                         observations=notes)
            for title, status, notes in
            (("Completed", InterventionStatus.COMPLETED, "Original"),
             ("Planned", InterventionStatus.PLANNED, None),
             ("Rollback target", InterventionStatus.COMPLETED, "Original"))
        ]
        db.add_all(interventions)
        await db.commit()
        ids = [u.id for u in users]
        jobs = [i.id for i in interventions]

    async def database():
        async with sessions() as db:
            yield db

    previous = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = database
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            yield client, sessions, ids, jobs
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
        await engine.dispose()
        if admin:
            async with admin.begin() as conn:
                await conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
            await admin.dispose()


async def test_private_report_versions_are_stable_and_manually_transmitted(context):
    client, sessions, (tech, other, admin), (completed, planned, rollback_target) = context
    def headers(user):
        return {"Authorization": "Bearer " + create_access_token(user)}
    async def call(method, path, *, who=tech, status=200, extra=None, **kwargs):
        res = await client.request(
            method, "/api/v1" + path, headers={**(headers(who) if who else {}), **(extra or {})},
            **kwargs,
        )
        assert res.status_code == status, (path, status, res.status_code, res.text[:500])
        return res

    assert (await call("GET", f"/interventions/{completed}/report/download", status=404)).status_code == 404
    async with sessions() as db:
        assert await db.scalar(select(func.count(Report.id))) == 0
    await call("POST", f"/interventions/{planned}/reports", status=400)
    await call("POST", f"/interventions/{completed}/reports", who=other, status=403)
    await call("POST", f"/interventions/{completed}/reports", who=None, status=401)
    first = (await call("POST", f"/interventions/{completed}/reports", status=201,
                        extra={"Idempotency-Key": "version-one"})).json()
    report_id = first["report_id"]
    assert first["version"] == 1 and first["status"] == "GENERATED" and first["size"] > 1000
    blob = (await call("GET", f"/reports/{report_id}/versions/1")).content
    assert blob.startswith(b"%PDF-") and len(blob) == first["size"]
    assert sha256(blob).hexdigest() == first["sha256"]
    replay = (await call("POST", f"/interventions/{completed}/reports", status=201,
                         extra={"Idempotency-Key": "version-one"})).json()
    assert replay["id"] == first["id"]
    await call("GET", f"/reports/{report_id}", who=other, status=403)
    await call("GET", f"/reports/{report_id}/versions/1", who=None, status=401)
    await call("POST", f"/reports/{report_id}/versions/1/transmit", json={"confirmed": False}, status=422)
    sent = (await call("POST", f"/reports/{report_id}/versions/1/transmit",
                       json={"confirmed": True})).json()
    repeated = (await call("POST", f"/reports/{report_id}/versions/1/transmit",
                           json={"confirmed": True}, who=admin)).json()
    assert sent["status"] == "TRANSMITTED"
    assert repeated["transmitted_at"] == sent["transmitted_at"]
    assert repeated["transmitted_by_id"] == sent["transmitted_by_id"] == tech
    await call("PUT", f"/interventions/{completed}", json={"observations": "Corrected"})
    second = (await call("POST", f"/interventions/{completed}/reports", status=201,
                         extra={"Idempotency-Key": "version-two"})).json()
    assert second["report_id"] == report_id and second["version"] == 2 and second["status"] == "GENERATED"
    newer = (await call("GET", f"/reports/{report_id}/versions/2")).content
    assert newer != blob and (await call("GET", f"/reports/{report_id}/versions/1")).content == blob
    assert (await call("GET", f"/interventions/{completed}/report/download")).content == newer
    listed = (await call("GET", f"/reports/{report_id}", who=admin)).json()
    assert [v["status"] for v in listed["versions"]] == ["TRANSMITTED", "GENERATED"]
    await call("DELETE", f"/interventions/{completed}", status=409)

    with patch.object(ReportExporter, "generate_pdf", side_effect=RuntimeError("renderer failure")):
        with pytest.raises(RuntimeError, match="renderer failure"):
            await call("POST", f"/interventions/{rollback_target}/reports", status=201)
    async with sessions() as db:
        assert await db.scalar(select(func.count(Report.id))) == 1
        assert await db.scalar(select(func.count(ReportVersion.id))) == 2
        assert await db.scalar(select(Report.id).where(Report.intervention_id == rollback_target)) is None
