"""Contrats R2/INT-114 : extraction customers, registre unique et API historique."""

import ast
from datetime import UTC, date, datetime
from importlib.util import resolve_name
from inspect import unwrap

import pytest

from tests.test_modular_bootstrap import BACKEND, ISOLATED_IMPORTS, _run_python

RETIRED_MODULES = tuple(
    f"app.{layer}.{name}"
    for layer, names in (
        ("models", ("client", "site")),
        ("schemas", ("client", "site")),
        ("repositories", ("client", "site")),
        ("services", ("client", "site")),
        ("api.v1", ("clients", "sites")),
    )
    for name in names
)


def test_customers_layout_and_no_retired_imports():
    package = BACKEND / "app/modules/customers"
    assert {path.name for path in package.glob("*.py")} == {
        "__init__.py", "models.py", "schemas.py", "repository.py", "service.py", "api.py",
    }
    init = ast.parse((package / "__init__.py").read_text(encoding="utf-8"))
    assert not init.body or (len(init.body) == 1 and ast.get_docstring(init) is not None)
    remaining = [name for name in RETIRED_MODULES
                 if (BACKEND / (name.replace(".", "/") + ".py")).exists()]
    assert not remaining, f"Anciens modules encore présents : {remaining}"
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
                        module = resolve_name("." * node.level + module,
                                              ".".join(path.parent.relative_to(BACKEND).parts))
                    modules = [module, *(module + "." + alias.name for alias in node.names)]
                else:
                    continue
                if any(name == old or name.startswith(old + ".")
                       for name in modules for old in RETIRED_MODULES):
                    violations.append(f"{path.relative_to(BACKEND)}:{node.lineno}")
    assert not violations, "Imports legacy restants : " + ", ".join(violations)


@pytest.mark.parametrize("module", ["models", "schemas"])
def test_customers_import_is_pure(tmp_path, module):
    _run_python(tmp_path, f"""
        from importlib import import_module
        from app.core.base import Base

        customers = import_module("app.modules.customers." + {module!r})
        if {module!r} == "models":
            assert set(Base.metadata.tables) == {{"client", "site"}}
            assert {{mapper.class_ for mapper in Base.registry.mappers}} == {{customers.Client, customers.Site}}
            assert customers.Client.__module__ == customers.Site.__module__ == customers.__name__
        else:
            assert not Base.metadata.tables
            assert not set(Base.registry.mappers)
            assert customers.ClientCreate(full_name="Owner", phone="01", address="Paris")
            assert customers.SiteCreate(client_id=1, name="A", address="Paris")
        """, forbidden=ISOLATED_IMPORTS + (
            "app.models", "app.modules.customers.api",
            "app.modules.customers.repository", "app.modules.customers.service",
        ))


@pytest.mark.parametrize("order", ["customer-first", "legacy-first"])
def test_customer_and_legacy_orders_preserve_registry_and_relations(tmp_path, order):
    _run_python(tmp_path, f"""
        import importlib
        from sqlalchemy import inspect
        from app.core.base import Base

        first = importlib.import_module(
            "app.modules.customers.models" if {order!r} == "customer-first" else "app.models"
        )
        tables = dict(Base.metadata.tables)
        mappers = set(Base.registry.mappers)
        from app.model_registry import load_models
        load_models()
        assert_registry(Base)
        customers = importlib.import_module("app.modules.customers.models")
        legacy = importlib.import_module("app.models")
        assert first.Client is legacy.Client is customers.Client
        assert first.Site is legacy.Site is customers.Site
        assert legacy.Base is Base
        assert all(Base.metadata.tables[name] is table for name, table in tables.items())
        assert mappers <= set(Base.registry.mappers)
        complete = set(Base.registry.mappers)
        load_models()
        assert_registry(Base)
        assert set(Base.registry.mappers) == complete
        for table in Base.metadata.tables.values():
            for fk in table.foreign_keys:
                assert fk.column.table is Base.metadata.tables[fk.column.table.key]
        assert inspect(customers.Client).relationships["sites"].mapper.class_ is customers.Site
        assert inspect(customers.Site).relationships["client"].mapper.class_ is customers.Client
        for name, target in (("equipment", legacy.Equipment), ("installations", legacy.Installation),
                             ("interventions", legacy.Intervention)):
            assert inspect(customers.Site).relationships[name].mapper.class_ is target
            assert inspect(target).relationships["site"].mapper.class_ is customers.Site
        """)


@pytest.fixture
async def context(tmp_path, monkeypatch):
    # Réutiliser le vrai JWT et la DB temporaire d'INT-103, jamais sa variante PG.
    monkeypatch.delenv("TERVO_INSTALLATION_TEST_DATABASE_URL", raising=False)
    from tests.test_installations import context as installation_context

    fixture = unwrap(installation_context)(tmp_path)
    try:
        yield await anext(fixture)
    finally:
        await fixture.aclose()


async def test_installation_blocks_deletion_without_losing_customer_data(context):
    from app.models.installation import Installation
    from app.modules.customers.models import Client, Site

    ac, sessions, (owner, site, other_site, _), _ = context
    response = await ac.post("/api/v1/installations", json={"site_id": site})
    assert response.status_code == 201, response.text
    installation = response.json()
    assert installation["equipment"] is None
    for path in (f"/api/v1/sites/{site}", f"/api/v1/clients/{owner}"):
        response = await ac.delete(path)
        assert response.status_code == 409, response.text
        assert "installations" in response.json()["detail"]
    async with sessions() as db:
        assert await db.get(Client, owner) is not None
        assert (await db.get(Site, site)).client_id == owner
        assert (await db.get(Installation, installation["id"])).site_id == site
    assert (await ac.delete(f"/api/v1/sites/{other_site}")).status_code == 204
    assert (await ac.get(f'/api/v1/installations/{installation["id"]}')).json() == installation


async def test_client_statistics_and_historical_site_routes(context):
    from app.models.intervention import Intervention
    from app.modules.customers.models import Client, Site

    ac, sessions, (owner, site, other_site, _), _ = context
    response = await ac.get(f"/api/v1/clients/{owner}")
    assert response.status_code == 200, response.text
    assert response.json()["interventions_count"] == 0
    assert response.json()["last_intervention_date"] is None
    response = await ac.post("/api/v1/equipment", json={"site_id": site})
    assert response.status_code == 201, response.text
    equipment = response.json()
    async with sessions() as db:
        outsider = Client(full_name="Other", phone="02", address="Lyon")
        db.add(outsider)
        await db.flush()
        outside_site = Site(client_id=outsider.id, name="Outside", address="Lyon")
        db.add(outside_site)
        await db.flush()
        rows = [Intervention(site_id=target, title=f"History {i}", scheduled_date=date(2026, 10, 1),
                             created_at=datetime(2026, 9, day, tzinfo=UTC),
                             equipment_id=equipment["id"] if i == 0 else None)
                for i, (target, day) in enumerate(((site, 1), (site, 2), (other_site, 3), (outside_site.id, 30)))]
        db.add_all(rows)
        await db.commit()
        expected = {rows[0].id, rows[1].id}
    response = await ac.get(f"/api/v1/clients/{owner}")
    assert response.status_code == 200, response.text
    assert response.json()["interventions_count"] == 3
    assert response.json()["last_intervention_date"] == "2026-09-03"
    response = await ac.get(f"/api/v1/sites/{site}/interventions")
    assert response.status_code == 200, response.text
    assert response.json()["total"] == 2
    assert {item["id"] for item in response.json()["items"]} == expected
    response = await ac.get(f"/api/v1/sites/{site}/equipment")
    assert response.status_code == 200, response.text
    assert response.json()["total"] == 1 and response.json()["items"] == [equipment]
    for suffix in ("interventions", "equipment"):
        response = await ac.get(f"/api/v1/sites/{other_site}/{suffix}")
        assert response.status_code == 200 and response.json()["total"] == (1 if suffix == "interventions" else 0)
        assert (await ac.get(f"/api/v1/sites/99999/{suffix}")).status_code == 404
