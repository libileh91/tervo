"""R5/INT-117 : cutover équipement et conservation physique, sans nouveau contrat."""

import ast
from importlib.util import resolve_name
from inspect import unwrap
from unittest.mock import AsyncMock, patch

import pytest

from tests.test_modular_bootstrap import BACKEND, ISOLATED_IMPORTS, _run_python

RETIRED_MODULES = (
    "app.models.equipment",
    "app.schemas.equipment",
    "app.repositories.equipment",
    "app.services.equipment",
    "app.api.v1.equipment",
)


def test_equipment_layout_and_cutover_imports():
    package = BACKEND / "app/modules/equipment"
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


@pytest.mark.parametrize("module", ["models", "schemas"])
def test_equipment_import_is_pure(tmp_path, module):
    _run_python(tmp_path, f"""
        from importlib import import_module
        from app.core.base import Base

        imported = import_module("app.modules.equipment." + {module!r})
        # Les schémas importent l'enum du modèle : cette table est attendue.
        assert set(Base.metadata.tables) == {{"equipment"}}
        models = import_module("app.modules.equipment.models")
        assert {{mapper.class_ for mapper in Base.registry.mappers}} == {{models.Equipment}}
        assert models.Equipment.__module__ == models.__name__
        assert models.EquipmentStatus.__module__ == models.__name__
        assert {{state.value for state in models.EquipmentStatus}} == {{
            "ACTIVE", "OUT_OF_SERVICE", "REPLACED", "RETIRED",
        }}
        if {module!r} == "schemas":
            assert imported.EquipmentStatus is models.EquipmentStatus
            body = imported.EquipmentCreate(site_id=1, lifecycle_status="OUT_OF_SERVICE")
            assert body.lifecycle_status is models.EquipmentStatus.OUT_OF_SERVICE
        """, forbidden=ISOLATED_IMPORTS + RETIRED_MODULES + (
            "app.models", "app.modules.equipment.api",
            "app.modules.equipment.service", "app.modules.equipment.repository",
        ))


@pytest.mark.parametrize("order", ["equipment-first", "registry-first"])
def test_equipment_import_orders_preserve_registry_and_relations(tmp_path, order):
    _run_python(tmp_path, f"""
        from importlib import import_module
        from sqlalchemy import inspect
        from app.core.base import Base

        from app.model_registry import load_models
        if {order!r} == "registry-first":
            load_models()
        first = import_module("app.modules.equipment.models")
        tables = dict(Base.metadata.tables)
        mappers = set(Base.registry.mappers)
        from app.model_registry import load_models
        load_models()
        assert_registry(Base)
        models = import_module("app.modules.equipment.models")
        from app.modules.installations.models import Installation
        from app.modules.interventions.models.intervention import Intervention
        customers = import_module("app.modules.customers.models")
        catalog = import_module("app.modules.catalog.models")
        assert first.Equipment is models.Equipment
        assert models.Base is Base
        assert len(Base.registry.mappers) == 17
        assert all(mapper.class_.metadata is Base.metadata for mapper in Base.registry.mappers)
        assert all(Base.metadata.tables[name] is table for name, table in tables.items())
        assert mappers <= set(Base.registry.mappers)
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
        equipment = models.Equipment
        for source, relation, target in (
            (equipment, "site", customers.Site),
            (customers.Site, "equipment", equipment),
            (equipment, "product", catalog.Product),
            (catalog.Product, "equipment", equipment),
            (equipment, "installation", Installation),
            (Installation, "equipment", equipment),
            (equipment, "interventions", Intervention),
            (Intervention, "equipment", equipment),
            (equipment, "replaced_by", equipment),
        ):
            assert inspect(source).relationships[relation].mapper.class_ is target
        assert equipment.__table__.c.installation_id.nullable
        assert equipment.__table__.c.installation_id.unique
        assert not inspect(Installation).relationships["equipment"].uselist
        """, forbidden=ISOLATED_IMPORTS + RETIRED_MODULES)


@pytest.fixture
async def context(tmp_path, monkeypatch):
    monkeypatch.delenv("TERVO_INSTALLATION_TEST_DATABASE_URL", raising=False)
    from tests.test_installations import context as installation_context

    fixture = unwrap(installation_context)(tmp_path)
    try:
        yield await anext(fixture)
    finally:
        await fixture.aclose()


async def test_technician_replacement_keeps_historical_orm_links(context):
    from datetime import date
    from sqlalchemy import func, select
    from sqlalchemy.orm import selectinload
    from app.modules.installations.models import Installation
    from app.modules.interventions.models.intervention import Intervention
    from app.modules.catalog.models import Product
    from app.modules.customers.models import Site
    from app.modules.equipment.models import Equipment, EquipmentStatus

    ac, sessions, (_, site_id, _, product_id), tokens = context
    ac.headers.update(tokens["technician"])
    # Seed an imported historical appliance, not another copy of API creation tests.
    async with sessions() as db:
        old_equipment = Equipment(
            site_id=site_id, product_id=product_id, serial_number="IMPORT-1999",
            installed_at=date(1999, 4, 3), commissioned_at=date(1999, 4, 5),
            notes="Historique importé", lifecycle_status=EquipmentStatus.OUT_OF_SERVICE,
        )
        db.add(old_equipment)
        await db.flush()
        intervention = Intervention(
            site_id=site_id, equipment_id=old_equipment.id,
            title="Historique terrain", scheduled_date=date(2026, 9, 24),
        )
        db.add(intervention)
        await db.commit()
        old_id, intervention_id = old_equipment.id, intervention.id
    response = await ac.post(f"/api/v1/equipment/{old_id}/replace", json={
        "serial_number": "NEW-2026", "installation_date": "2026-09-28",
    })
    assert response.status_code == 201, response.text
    new_id = response.json()["id"]
    # Product deliberately omitted on the new instance: old provenance must survive.
    before = (await ac.get(f"/api/v1/equipment/{old_id}")).json()
    for target, payload, code in (
        (old_id, {}, 409),
        (new_id, {"new_product_id": 999999}, 404),
    ):
        response = await ac.post(f"/api/v1/equipment/{target}/replace", json=payload)
        assert response.status_code == code, response.text
    assert (await ac.get(f"/api/v1/equipment/{old_id}")).json() == before
    listing = await ac.get("/api/v1/equipment", params={"site_id": site_id})
    assert listing.status_code == 200
    assert {item["id"] for item in listing.json()["items"]} == {old_id, new_id}
    async with sessions() as db:
        old_equipment = await db.scalar(select(Equipment).where(Equipment.id == old_id).options(
            selectinload(Equipment.site), selectinload(Equipment.product),
            selectinload(Equipment.installation), selectinload(Equipment.interventions),
            selectinload(Equipment.replaced_by),
        ))
        new_equipment = old_equipment.replaced_by
        assert new_equipment is await db.get(Equipment, new_id)
        assert old_equipment.site is await db.get(Site, site_id)
        assert new_equipment.site_id == old_equipment.site_id
        assert old_equipment.product is await db.get(Product, product_id)
        assert new_equipment.product_id is None
        assert old_equipment.serial_number == "IMPORT-1999"
        assert old_equipment.installed_at == date(1999, 4, 3)
        assert old_equipment.commissioned_at == date(1999, 4, 5)
        assert old_equipment.notes == "Historique importé"
        assert old_equipment.lifecycle_status is EquipmentStatus.REPLACED
        assert new_equipment.lifecycle_status is EquipmentStatus.ACTIVE
        assert new_equipment.replaced_by_id is None
        assert new_equipment.serial_number == "NEW-2026"
        assert new_equipment.installed_at == date(2026, 9, 28)
        assert old_equipment.installation_id is new_equipment.installation_id is None
        assert old_equipment.installation is None
        assert old_equipment.interventions == [await db.get(Intervention, intervention_id)]
        assert old_equipment.interventions[0].equipment_id == old_id
        assert await db.scalar(select(func.count(Equipment.id))) == 2
        assert await db.scalar(select(func.count(Installation.id))) == 0


@pytest.mark.parametrize("failure_at", ["flush", "execute", "commit"])
async def test_repository_replace_rolls_back_after_controlled_failure(context, failure_at):
    from sqlalchemy import func, select
    from app.modules.equipment.models import Equipment, EquipmentStatus
    from app.modules.equipment.repository import EquipmentRepository

    _, sessions, (_, site_id, _, product_id), _ = context
    async with sessions() as db:
        old_equipment = Equipment(site_id=site_id, product_id=product_id, serial_number="KEEP")
        db.add(old_equipment)
        await db.commit()
        old_id = old_equipment.id
        failure = RuntimeError("controlled replacement failure")
        with patch.object(db, failure_at, AsyncMock(side_effect=failure)):
            with patch.object(db, "rollback", AsyncMock(wraps=db.rollback)) as rollback:
                with pytest.raises(RuntimeError) as raised:
                    await EquipmentRepository(db).replace(old_equipment, {"serial_number": "DISCARD"})
                assert raised.value is failure
                rollback.assert_awaited_once()
        # A fresh session checks persisted state, not expired/identity-map values.
    async with sessions() as db:
        stored = await db.get(Equipment, old_id)
        assert stored.serial_number == "KEEP" and stored.product_id == product_id
        assert stored.lifecycle_status is EquipmentStatus.ACTIVE
        assert stored.replaced_by_id is None
        assert await db.scalar(select(func.count(Equipment.id))) == 1
