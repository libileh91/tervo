"""R10 dashboard extraction: preserve technician-scoped, read-only aggregation."""
import ast
from datetime import date, datetime, time, timedelta
import importlib
import os
from pathlib import Path
import subprocess
import sys

import pytest
from sqlalchemy import event, select

BACKEND = Path(__file__).resolve().parents[1]
DTO_NAMES = {
    "TodaySummary", "NextInterventionRef", "InProgressInterventionRef",
    "OverdueInterventionRef", "DashboardSummaryResponse",
}
SCHEMA_SNAPSHOT = """
class TodaySummary(BaseModel):
    date: date | str
    interventions_total: int = 0
    interventions_in_progress: int = 0
    interventions_completed: int = 0
class NextInterventionRef(BaseModel):
    id: int
    title: str
    priority: str
    site_name: str
    site_address: str
    scheduled_start_time: time | None = None
class InProgressInterventionRef(BaseModel):
    id: int
    title: str
    started_at: datetime
    elapsed_minutes: int = 0
class OverdueInterventionRef(BaseModel):
    id: int
    title: str
    priority: str
    scheduled_date: str
    days_overdue: int
    site_name: str
    site_address: str
class DashboardSummaryResponse(BaseModel):
    today: TodaySummary
    next_intervention: NextInterventionRef | None = None
    in_progress_intervention: InProgressInterventionRef | None = None
    overdue_interventions: list[OverdueInterventionRef] = []
"""


def test_layout_and_frozen_dto_ast():
    module = BACKEND / "app/modules/dashboard"
    assert {p.name for p in module.iterdir() if p.name != "__pycache__"} == {
        "__init__.py", "api.py", "schemas.py", "service.py",
    }
    init = ast.parse((module / "__init__.py").read_text())
    assert all(isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant)
               and isinstance(node.value.value, str) for node in init.body)
    assert not (BACKEND / "app/api/v1/dashboard.py").exists()
    actual = ast.parse((module / "schemas.py").read_text())
    classes = [node for node in actual.body if isinstance(node, ast.ClassDef)]
    assert {node.name for node in classes} == DTO_NAMES
    assert [ast.dump(node) for node in classes] == [
        ast.dump(node) for node in ast.parse(SCHEMA_SNAPSHOT).body
    ]
    old = ast.parse((BACKEND / "app/modules/interventions/schemas/intervention.py").read_text())
    assert not any(isinstance(node, ast.ClassDef) and node.name in DTO_NAMES for node in old.body)


def test_package_and_schemas_import_without_database(tmp_path):
    env = {key: value for key, value in os.environ.items() if not key.startswith("TERVO_")}
    env.update(PYTHONPATH=str(BACKEND), PYTHONDONTWRITEBYTECODE="1",
               DATABASE_URL=f"sqlite:///{tmp_path / 'unused.db'}",
               UPLOAD_DIR=str(tmp_path / "uploads"))
    result = subprocess.run([sys.executable, "-B", "-c", """
import sys
from importlib.abc import MetaPathFinder
class Guard(MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in {"sqlalchemy", "asyncpg", "aiosqlite"}:
            raise AssertionError(fullname)
sys.meta_path.insert(0, Guard())
import app.modules.dashboard
assert "app.modules.dashboard.api" not in sys.modules
assert "app.modules.dashboard.service" not in sys.modules
assert "app.modules.dashboard.schemas" not in sys.modules
import app.modules.dashboard.schemas
assert "app.modules.dashboard.api" not in sys.modules
assert "app.modules.dashboard.service" not in sys.modules
"""], cwd=tmp_path, env=env, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    assert not (tmp_path / "unused.db").exists()


@pytest.fixture
async def context(tmp_path, monkeypatch):
    monkeypatch.delenv("TERVO_INSTALLATION_TEST_DATABASE_URL", raising=False)
    from tests.test_installations import context as installation_context
    generator = installation_context.__wrapped__(tmp_path)
    try:
        yield await anext(generator)
    finally:
        await generator.aclose()


class FrozenDatetime(datetime):
    @classmethod
    def utcnow(cls):
        # The repository reads date.today() locally. Use that same calendar day
        # everywhere, and fix only the UTC time used for elapsed minutes.
        return cls.combine(date.today(), time(12, 0, 59))


@pytest.mark.parametrize("populated", [False, True], ids=["empty", "multi-user-history"])
async def test_real_service_and_http_readonly(context, monkeypatch, populated):
    from app.modules.identity.models import User
    from app.modules.interventions.models.intervention import Intervention, InterventionStatus
    service_module = importlib.import_module("app.modules.dashboard.service")
    monkeypatch.setattr(service_module, "datetime", FrozenDatetime)
    ac, sessions, (_, site, _, _), tokens = context
    today = date.today()
    started_yesterday = datetime.combine(today - timedelta(days=1), time(11, 30))
    async with sessions() as db:
        users = {user.username: user for user in (await db.scalars(select(User))).all()}
        technician, admin = users["technician"], users["admin"]
        items = {}
        if populated:
            def item(name, owner, day, status, hour=9, started=None):
                row = Intervention(title=name, site_id=site, technician_id=owner.id,
                                   scheduled_date=day, scheduled_start_time=time(hour),
                                   status=status, started_at=started)
                items[name] = row
                db.add(row)
            item("next", technician, today, InterventionStatus.PLANNED, 8)
            item("later", technician, today, InterventionStatus.PLANNED, 10)
            item("tomorrow", technician, today + timedelta(days=1), InterventionStatus.PLANNED, 7)
            item("running-yesterday", technician, today - timedelta(days=1),
                 InterventionStatus.IN_PROGRESS, started=started_yesterday)
            item("completed-history", technician, today - timedelta(days=30), InterventionStatus.COMPLETED)
            item("completed-today", technician, today, InterventionStatus.COMPLETED)
            item("overdue", technician, today - timedelta(days=3), InterventionStatus.PLANNED)
            item("admin-today", admin, today, InterventionStatus.PLANNED)
            item("admin-overdue", admin, today - timedelta(days=5), InterventionStatus.PLANNED)
            item("admin-completed", admin, today - timedelta(days=2), InterventionStatus.COMPLETED)
            await db.commit()
        engine = db.bind.sync_engine
        def only_reads(connection, cursor, statement, parameters, context, executemany):
            assert statement.lstrip().upper().startswith(("SELECT", "PRAGMA")), statement
        def no_commit(connection):
            raise AssertionError("Dashboard committed a transaction")
        event.listen(engine, "before_cursor_execute", only_reads)
        event.listen(engine, "commit", no_commit)
        try:
            direct = await service_module.DashboardService(db).get_dashboard_summary(technician)
            response = await ac.get("/api/v1/dashboard/summary")
            assert response.status_code == 200, response.text
            body = response.json()
            assert body == direct.model_dump(mode="json")
            assert body["today"] == {
                "date": today.isoformat(), "interventions_total": 4 if populated else 0,
                "interventions_in_progress": 1 if populated else 0,
                "interventions_completed": 2 if populated else 0,
            }
            if populated:
                assert body["next_intervention"] == {
                    "id": items["next"].id, "title": "next", "priority": items["next"].priority.value,
                    "site_name": "A", "site_address": "A", "scheduled_start_time": "08:00:00",
                }
                assert body["in_progress_intervention"] == {
                    "id": items["running-yesterday"].id, "title": "running-yesterday",
                    "started_at": started_yesterday.isoformat(), "elapsed_minutes": 1470,
                }
                assert body["overdue_interventions"] == [{
                    "id": items["overdue"].id, "title": "overdue",
                    "priority": items["overdue"].priority.value,
                    "scheduled_date": (today - timedelta(days=3)).isoformat(), "days_overdue": 3,
                    "site_name": "A", "site_address": "A",
                }]
            else:
                assert body["next_intervention"] is None
                assert body["in_progress_intervention"] is None
                assert body["overdue_interventions"] == []
            response = await ac.get("/api/v1/dashboard/summary", headers=tokens["admin"])
            assert response.status_code == 200, response.text
            admin_body = response.json()
            assert admin_body["today"]["interventions_total"] == (1 if populated else 0)
            assert admin_body["today"]["interventions_completed"] == (1 if populated else 0)
            assert admin_body["in_progress_intervention"] is None
            if populated:
                assert admin_body["next_intervention"]["id"] == items["admin-today"].id
                assert [row["id"] for row in admin_body["overdue_interventions"]] == [items["admin-overdue"].id]
            for authorization in (None, "Bearer invalid.jwt"):
                request = ac.build_request("GET", "/api/v1/dashboard/summary")
                request.headers.pop("authorization", None)
                if authorization:
                    request.headers["authorization"] = authorization
                assert (await ac.send(request)).status_code in (401, 403)
        finally:
            event.remove(engine, "before_cursor_execute", only_reads)
            event.remove(engine, "commit", no_commit)
