"""R6/INT-118 : cutover Installation et transaction commerciale inchangée."""

import ast
from importlib.util import resolve_name
from inspect import unwrap
from unittest.mock import AsyncMock, patch

import pytest

from tests.test_modular_bootstrap import BACKEND, ISOLATED_IMPORTS, _run_python

RETIRED_MODULES = (
    "app.models.installation",
    "app.schemas.installation",
    "app.repositories.installation",
    "app.services.installation",
    "app.api.v1.installations",
)


def test_installations_layout_and_cutover_imports():
    package = BACKEND / "app/modules/installations"
    assert {path.name for path in package.glob("*.py")} == {
        "__init__.py", "models.py", "schemas.py", "repository.py", "service.py", "api.py",
    }
    tree = ast.parse((package / "__init__.py").read_text(encoding="utf-8"))
    assert not tree.body or (len(tree.body) == 1 and ast.get_docstring(tree) is not None)
    assert not [
        name for name in RETIRED_MODULES
        if (BACKEND / (name.replace(".", "/") + ".py")).exists()
    ]
    violations = []
    for root in (BACKEND / "app", BACKEND / "tests"):
        for path in root.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    modules = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    if node.level:
                        module = resolve_name(
                            "." * node.level + module,
                            ".".join(path.parent.relative_to(BACKEND).parts),
                        )
                    modules = [module, *(module + "." + alias.name for alias in node.names)]
                else:
                    continue
                if any(name == old or name.startswith(old + ".")
                       for name in modules for old in RETIRED_MODULES):
                    violations.append(f"{path.relative_to(BACKEND)}:{node.lineno}")
    assert not violations, "Imports legacy restants : " + ", ".join(violations)


def test_installations_package_init_has_no_side_effects(tmp_path):
    _run_python(tmp_path, """
        from importlib import import_module
        from app.core.base import Base

        import_module("app.modules.installations")
        assert not Base.metadata.tables
        assert not list(Base.registry.mappers)
        """, forbidden=ISOLATED_IMPORTS + RETIRED_MODULES + (
            "app.models", "app.modules.installations.models",
            "app.modules.installations.schemas", "app.modules.installations.repository",
            "app.modules.installations.service", "app.modules.installations.api",
        ))


@pytest.mark.parametrize("module", ["models", "schemas"])
def test_installations_import_is_pure(tmp_path, module):
    _run_python(tmp_path, f"""
        from importlib import import_module
        from app.core.base import Base

        imported = import_module("app.modules.installations." + {module!r})
        models = import_module("app.modules.installations.models")
        expected = {{"installation"}}
        classes = {{models.Installation}}
        if {module!r} == "schemas":
            # InstallationResponse embeds EquipmentResponse and its local enum.
            equipment = import_module("app.modules.equipment.models")
            expected.add("equipment")
            classes.add(equipment.Equipment)
            assert imported.InstallationStatus is models.InstallationStatus
        assert set(Base.metadata.tables) == expected
        assert {{mapper.class_ for mapper in Base.registry.mappers}} == classes
        assert models.Installation.__module__ == models.__name__
        assert models.InstallationStatus.__module__ == models.__name__
        assert {{state.value for state in models.InstallationStatus}} == {{
            "SCHEDULED", "IN_PROGRESS", "COMPLETED", "CANCELLED",
        }}
        """, forbidden=ISOLATED_IMPORTS + RETIRED_MODULES + (
            "app.models", "app.modules.installations.api",
            "app.modules.installations.service", "app.modules.installations.repository",
        ))


@pytest.mark.parametrize("order", ["installations-first", "registry-first"])
def test_installations_registry_identity_and_relations(tmp_path, order):
    _run_python(tmp_path, f"""
        from importlib import import_module
        from sqlalchemy import inspect
        from app.core.base import Base

        from app.model_registry import load_models
        if {order!r} == "registry-first":
            load_models()
        first = import_module("app.modules.installations.models")
        tables = dict(Base.metadata.tables)
        mappers = set(Base.registry.mappers)
        from app.model_registry import load_models
        load_models()
        assert_registry(Base)
        models = import_module("app.modules.installations.models")
        customers = import_module("app.modules.customers.models")
        sales = import_module("app.modules.sales.models")
        equipment = import_module("app.modules.equipment.models")
        assert first.Installation is models.Installation
        assert models.Base is Base
        assert all(mapper.class_.metadata is Base.metadata for mapper in Base.registry.mappers)
        assert mappers <= set(Base.registry.mappers)
        assert all(Base.metadata.tables[name] is table for name, table in tables.items())
        complete_tables = dict(Base.metadata.tables)
        complete_mappers = set(Base.registry.mappers)
        load_models()
        assert_registry(Base)
        assert set(Base.registry.mappers) == complete_mappers
        assert set(Base.metadata.tables) == set(complete_tables)
        assert all(Base.metadata.tables[name] is table for name, table in complete_tables.items())
        for table in Base.metadata.tables.values():
            for fk in table.foreign_keys:
                assert fk.column.table is Base.metadata.tables[fk.column.table.key]
        for source, relation, target in (
            (models.Installation, "site", customers.Site),
            (customers.Site, "installations", models.Installation),
            (models.Installation, "sale_line", sales.SaleLine),
            (sales.SaleLine, "installations", models.Installation),
            (models.Installation, "equipment", equipment.Equipment),
            (equipment.Equipment, "installation", models.Installation),
        ):
            assert inspect(source).relationships[relation].mapper.class_ is target
        assert not inspect(models.Installation).relationships["equipment"].uselist
        assert models.Installation.__table__.c.sale_line_id.nullable
        assert equipment.Equipment.__table__.c.installation_id.unique
        """, forbidden=ISOLATED_IMPORTS + RETIRED_MODULES)


def test_installations_router_is_composed_once(tmp_path):
    _run_python(tmp_path, """
        from fastapi import routing
        from fastapi.routing import APIRoute
        from app.main import app
        from app.modules.installations.api import router

        # Same effective-route rule as the bootstrap contract: recent FastAPI
        # versions keep deferred inclusions rather than copied APIRoutes.
        iterator = getattr(routing, "_iter_routes_with_context", None)
        routes = (
            iterator(app.routes) if iterator is not None
            else ((route, None) for route in app.routes)
        )
        local = [route for route in router.routes if isinstance(route, APIRoute)]
        composed = [
            context if context is not None else route
            for route, context in routes if isinstance(route, APIRoute)
            and (context if context is not None else route).path.startswith("/api/v1/installations")
        ]
        assert len(local) == len(composed) == 6
        for route in local:
            matches = [
                candidate for candidate in composed
                if candidate.path == "/api/v1" + route.path
                and candidate.methods == route.methods
            ]
            assert len(matches) == 1
            assert matches[0].endpoint is route.endpoint
        """, forbidden=RETIRED_MODULES, block_engine=False)


def test_installations_schema_contracts_are_preserved():
    from datetime import datetime
    from pydantic import ValidationError
    from app.modules.installations.schemas import InstallationComplete, InstallationCreate

    body = InstallationCreate(
        site_id=1, sale_line_id=2,
        scheduled_start="2026-09-28T10:00:00+02:00",
        scheduled_end="2026-09-28T08:00:00Z",
    )
    assert body.scheduled_start == body.scheduled_end == datetime(2026, 9, 28, 8)
    assert InstallationCreate(site_id=1).sale_line_id is None
    # No implicit requirement for a product on autonomous create completion.
    complete = InstallationComplete(
        installation_date="2026-09-28", equipment={"mode": "create"},
    )
    assert complete.equipment.product_id is None
    with pytest.raises(ValidationError):
        InstallationCreate(site_id=1, status="COMPLETED")
    with pytest.raises(ValidationError):
        InstallationComplete(
            installation_date="2026-09-28",
            equipment={"mode": "attach", "equipment_id": 1, "product_id": 2},
        )


@pytest.fixture
async def context(tmp_path, monkeypatch):
    monkeypatch.delenv("TERVO_INSTALLATION_TEST_DATABASE_URL", raising=False)
    from tests.test_installations import context as installation_context

    fixture = unwrap(installation_context)(tmp_path)
    try:
        yield await anext(fixture)
    finally:
        await fixture.aclose()


async def _commercial_installation(context, mode, role):
    ac, _, (client_id, site_id, _, product_id), tokens = context
    ac.headers.update(tokens[role])
    response = await ac.post("/api/v1/sales", json={
        "client_id": client_id, "site_id": site_id, "sale_date": "2026-09-28",
        "lines": [{"product_id": product_id, "quantity": 1, "unit_price": "1250.50"}],
    })
    assert response.status_code == 201, response.text
    sale = response.json()
    response = await ac.post(f'/api/v1/sales/{sale["id"]}/confirm')
    assert response.status_code == 200, response.text
    line_id = sale["lines"][0]["id"]
    response = await ac.post("/api/v1/installations", json={
        "site_id": site_id, "sale_line_id": line_id, "technician_notes": "Provenance R6",
    })
    assert response.status_code == 201, response.text
    installation_id = response.json()["id"]
    response = await ac.post(f"/api/v1/installations/{installation_id}/start")
    assert response.status_code == 200, response.text
    equipment = {"mode": mode, "product_id": product_id, "serial_number": "R6-CREATE"}
    equipment_id = None
    if mode == "attach":
        response = await ac.post("/api/v1/equipment", json={
            "site_id": site_id, "product_id": product_id, "serial_number": "R6-KEEP",
            "notes": "Historique conservé",
        })
        assert response.status_code == 201, response.text
        equipment_id = response.json()["id"]
        equipment = {"mode": mode, "equipment_id": equipment_id}
    return installation_id, line_id, equipment_id, {
        "installation_date": "2026-09-28", "commissioning_date": "2026-09-29",
        "equipment": equipment,
    }


@pytest.mark.parametrize("mode", ["create", "attach"])
@pytest.mark.parametrize("role", ["admin", "technician"])
async def test_commercial_completion_uses_one_session_and_service_commit(context, mode, role):
    from app.modules.installations.repository import InstallationRepository
    from app.modules.installations.schemas import InstallationComplete, InstallationResponse
    from app.modules.installations.service import InstallationService

    installation_id, line_id, equipment_id, payload = await _commercial_installation(context, mode, role)
    _, sessions, (_, site_id, _, product_id), _ = context
    async with sessions() as db:
        service = InstallationService(db)
        assert isinstance(service.repo, InstallationRepository)
        assert service.db is service.repo.db is service.references.db is service.references.repo.db is db
        write = "create_equipment" if mode == "create" else "attach_equipment"
        original = getattr(service.repo, write)
        with patch.object(db, "commit", AsyncMock(wraps=db.commit)) as commit:
            with patch.object(db, "rollback", AsyncMock(wraps=db.rollback)) as rollback:
                async def repository_write(*args, **kwargs):
                    result = await original(*args, **kwargs)
                    # Repository has really written, but has not committed.
                    commit.assert_not_awaited()
                    return result

                with patch.object(service.repo, write, AsyncMock(side_effect=repository_write)) as operation:
                    stored = await service.complete(installation_id, InstallationComplete(**payload))
                operation.assert_awaited_once()
                commit.assert_awaited_once()
                rollback.assert_not_awaited()
        response = InstallationResponse.model_validate(stored).model_dump(mode="json")
        assert response["status"] == "COMPLETED"
        assert response["sale_line_id"] == line_id
        assert response["technician_notes"] == "Provenance R6"
        equipment = response["equipment"]
        assert equipment["installation_id"] == installation_id
        assert equipment["site_id"] == site_id and equipment["product_id"] == product_id
        assert equipment["installed_at"] == payload["installation_date"]
        assert equipment["commissioned_at"] == payload["commissioning_date"]
        if mode == "attach":
            assert equipment["id"] == equipment_id
            assert equipment["serial_number"] == "R6-KEEP"
            assert equipment["notes"] == "Historique conservé"
    ac = context[0]
    response = await ac.get(f"/api/v1/installations/{installation_id}")
    assert response.status_code == 200, response.text
    assert response.json() == InstallationResponse.model_validate(stored).model_dump(mode="json")


@pytest.mark.parametrize("mode", ["create", "attach"])
async def test_commercial_completion_rolls_back_after_both_writes(context, mode):
    from sqlalchemy import func, select
    from app.modules.equipment.models import Equipment
    from app.modules.installations.models import Installation, InstallationStatus
    from app.modules.installations.schemas import InstallationComplete
    from app.modules.installations.service import InstallationService
    from app.modules.sales.models import SaleLine, SaleStatus

    installation_id, line_id, equipment_id, payload = await _commercial_installation(
        context, mode, "technician",
    )
    _, sessions, _, _ = context
    failure = RuntimeError("controlled failure after commercial completion writes")
    async with sessions() as db:
        service = InstallationService(db)

        async def reject_commit():
            # Read SQL state, not the stale Installation instance: both writes
            # have happened before the injected failure.
            assert await db.scalar(select(Installation.status).where(
                Installation.id == installation_id,
            )) is InstallationStatus.COMPLETED
            assert await db.scalar(select(func.count(Equipment.id)).where(
                Equipment.installation_id == installation_id,
            )) == 1
            raise failure

        with patch.object(db, "commit", AsyncMock(side_effect=reject_commit)) as commit:
            with patch.object(db, "rollback", AsyncMock(wraps=db.rollback)) as rollback:
                with pytest.raises(RuntimeError) as raised:
                    await service.complete(installation_id, InstallationComplete(**payload))
                assert raised.value is failure
                commit.assert_awaited_once()
                rollback.assert_awaited_once()
    async with sessions() as db:
        stored = await db.get(Installation, installation_id)
        assert stored.status is InstallationStatus.IN_PROGRESS
        assert stored.sale_line_id == line_id and stored.started_at is not None
        assert stored.completed_at is stored.installation_date is stored.commissioning_date is None
        assert await db.scalar(select(func.count(Equipment.id))) == int(mode == "attach")
        assert await db.scalar(select(func.count(Equipment.id)).where(
            Equipment.installation_id.is_not(None),
        )) == 0
        line = await db.get(SaleLine, line_id)
        from app.modules.sales.models import Sale
        assert (await db.get(Sale, line.sale_id)).status is SaleStatus.CONFIRMED
        assert line.quantity == 1
        if mode == "attach":
            equipment = await db.get(Equipment, equipment_id)
            assert equipment.installation_id is equipment.installed_at is equipment.commissioned_at is None
            assert equipment.serial_number == "R6-KEEP"
            assert equipment.notes == "Historique conservé"
