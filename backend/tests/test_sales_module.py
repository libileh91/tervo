"""Contrats R4/INT-116 : extraction sales, registre unique et provenance ORM."""

import ast
from decimal import Decimal
from importlib.util import resolve_name
from inspect import unwrap

import pytest

from tests.test_modular_bootstrap import BACKEND, ISOLATED_IMPORTS, _run_python

RETIRED_MODULES = (
    "app.models.sale",
    "app.schemas.sale",
    "app.services.sale",
    "app.api.v1.sales",
)


def test_sales_layout_and_no_retired_imports():
    package = BACKEND / "app/modules/sales"
    assert {path.name for path in package.glob("*.py")} == {
        "__init__.py", "models.py", "schemas.py", "service.py", "api.py",
    }
    assert not (package / "repository.py").exists()
    init = ast.parse((package / "__init__.py").read_text(encoding="utf-8"))
    assert not init.body or (len(init.body) == 1 and ast.get_docstring(init) is not None)
    remaining = [
        name for name in RETIRED_MODULES
        if (BACKEND / (name.replace(".", "/") + ".py")).exists()
    ]
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
def test_sales_import_is_pure(tmp_path, module):
    _run_python(tmp_path, f"""
        from importlib import import_module
        from decimal import Decimal
        from app.core.base import Base

        imported = import_module("app.modules.sales." + {module!r})
        assert set(Base.metadata.tables) == {{"sale", "sale_line"}}
        sales = import_module("app.modules.sales.models")
        # Les schémas importent l'enum local : les deux tables sont attendues.
        assert set(Base.metadata.tables) == {{"sale", "sale_line"}}
        assert {{mapper.class_ for mapper in Base.registry.mappers}} == {{sales.Sale, sales.SaleLine}}
        assert sales.Sale.__module__ == sales.SaleLine.__module__ == sales.__name__
        if {module!r} == "schemas":
            assert imported.SaleStatus is sales.SaleStatus
            body = imported.SaleCreate(
                client_id=1, site_id=2, sale_date="2026-10-01",
                lines=[{{"product_id": 3, "quantity": 3, "unit_price": "1250.50"}}],
            )
            assert body.lines[0].unit_price == Decimal("1250.50")
        """, forbidden=ISOLATED_IMPORTS + RETIRED_MODULES + (
            "app.models", "app.modules.sales.api", "app.modules.sales.service",
            "app.modules.sales.repository",
        ))


@pytest.mark.parametrize("order", ["sales-first", "registry-first"])
def test_sales_and_registry_orders_preserve_registry_and_relations(tmp_path, order):
    _run_python(tmp_path, f"""
        from importlib import import_module
        from sqlalchemy import inspect
        from app.core.base import Base

        from app.model_registry import load_models
        if {order!r} == "registry-first":
            load_models()
        first = import_module("app.modules.sales.models")
        tables = dict(Base.metadata.tables)
        mappers = set(Base.registry.mappers)
        from app.model_registry import load_models
        load_models()
        assert_registry(Base)
        sales = import_module("app.modules.sales.models")
        from app.modules.installations.models import Installation
        customers = import_module("app.modules.customers.models")
        catalog = import_module("app.modules.catalog.models")
        assert first.Sale is sales.Sale
        assert first.SaleLine is sales.SaleLine
        assert first.SaleStatus is sales.SaleStatus
        assert sales.Base is Base
        assert len(Base.registry.mappers) == 23
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
        for source, relation, target in (
            (sales.Sale, "client", customers.Client),
            (customers.Client, "sales", sales.Sale),
            (sales.Sale, "site", customers.Site),
            (customers.Site, "sales", sales.Sale),
            (sales.Sale, "lines", sales.SaleLine),
            (sales.SaleLine, "sale", sales.Sale),
            (sales.SaleLine, "product", catalog.Product),
            (sales.SaleLine, "installations", Installation),
            (Installation, "sale_line", sales.SaleLine),
            (Installation, "site", customers.Site),
        ):
            assert inspect(source).relationships[relation].mapper.class_ is target
        """, forbidden=ISOLATED_IMPORTS + RETIRED_MODULES)


@pytest.fixture
async def context(tmp_path, monkeypatch):
    # JWT réels et FK SQLite ; ne jamais hériter de la variante PostgreSQL.
    monkeypatch.delenv("TERVO_INSTALLATION_TEST_DATABASE_URL", raising=False)
    from tests.test_installations import context as installation_context

    fixture = unwrap(installation_context)(tmp_path)
    try:
        yield await anext(fixture)
    finally:
        await fixture.aclose()


async def test_authenticated_sale_relations_survive_site_rejection(context):
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from app.modules.installations.models import Installation
    from app.modules.catalog.models import Product
    from app.modules.customers.models import Client, Site
    from app.modules.sales.models import Sale, SaleLine, SaleStatus
    from app.modules.sales.service import SaleService

    ac, sessions, (client_id, site_id, other_site_id, product_id), tokens = context
    ac.headers.update(tokens["technician"])
    response = await ac.post("/api/v1/sales", json={
        "client_id": client_id, "site_id": site_id, "sale_date": "2026-10-01",
        "notes": "Provenance R4", "lines": [{
            "product_id": product_id, "quantity": 3, "unit_price": "1250.50",
            "description": "Prix contractuel",
        }],
    })
    assert response.status_code == 201, response.text
    sale = response.json()
    assert sale["status"] == "DRAFT"
    assert len(sale["lines"]) == 1
    line_id = sale["lines"][0]["id"]
    response = await ac.post(f'/api/v1/sales/{sale["id"]}/confirm')
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "CONFIRMED"
    response = await ac.post("/api/v1/installations", json={
        "site_id": site_id, "sale_line_id": line_id,
    })
    assert response.status_code == 201, response.text
    installation_ids = {response.json()["id"]}
    response = await ac.post("/api/v1/installations", json={
        "site_id": other_site_id, "sale_line_id": line_id,
    })
    assert response.status_code == 422, response.text

    # Complète INT-102 : traverser les relations déplacées dans une vraie session,
    # après le refus, sans inventer de GET détail sales ni simuler l'authentification.
    async with sessions() as db:
        stored = await SaleService(db).get(sale["id"])
        assert isinstance(stored, Sale)
        assert stored.status is SaleStatus.CONFIRMED
        assert stored.notes == "Provenance R4"
        assert len(stored.lines) == 1
        line = stored.lines[0]
        assert isinstance(line, SaleLine)
        assert (line.id, line.quantity, line.unit_price, line.description) == (
            line_id, 3, Decimal("1250.50"), "Prix contractuel",
        )
        loaded = await db.scalar(select(Sale).where(Sale.id == stored.id).options(
            selectinload(Sale.client), selectinload(Sale.site),
            selectinload(Sale.lines).selectinload(SaleLine.product),
            selectinload(Sale.lines).selectinload(SaleLine.installations),
        ))
        assert loaded is stored
        assert stored.client is await db.get(Client, client_id)
        assert stored.site is await db.get(Site, site_id)
        assert stored.site.client_id == stored.client.id
        assert line.product is await db.get(Product, product_id)
        assert {item.id for item in line.installations} == installation_ids
        installations = (await db.scalars(select(Installation).where(
            Installation.sale_line_id == line_id,
        ).options(selectinload(Installation.sale_line)))).all()
        assert {item.id for item in installations} == installation_ids
        assert all(item.sale_line is line and item.site_id == site_id for item in installations)
        assert line.sale is stored


@pytest.mark.parametrize("invalid_line", [
    {"quantity": 0},
    {"quantity": -1},
    {"unit_price": "-0.01"},
    {"unit_price": "1250.501"},
])
async def test_invalid_commercial_values_do_not_persist(context, invalid_line):
    from sqlalchemy import func, select
    from app.modules.sales.models import Sale, SaleLine

    ac, sessions, (client_id, site_id, _, product_id), tokens = context
    ac.headers.update(tokens["admin"])
    async with sessions() as db:
        before = (
            await db.scalar(select(func.count(Sale.id))),
            await db.scalar(select(func.count(SaleLine.id))),
        )
    response = await ac.post("/api/v1/sales", json={
        "client_id": client_id, "site_id": site_id, "sale_date": "2026-10-01",
        "lines": [{
            "product_id": product_id, "quantity": 3, "unit_price": "1250.50",
            **invalid_line,
        }],
    })
    assert response.status_code == 422, response.text
    async with sessions() as db:
        assert (
            await db.scalar(select(func.count(Sale.id))),
            await db.scalar(select(func.count(SaleLine.id))),
        ) == before


@pytest.mark.parametrize(("reference", "status", "detail"), [
    ("client", 404, "Client non trouvé"),
    ("site", 404, "Site non trouvé"),
    ("product", 404, "Produit non trouvé"),
    ("foreign-site", 422, "Le site ne dépend pas du client indiqué"),
])
async def test_invalid_references_do_not_persist(context, reference, status, detail):
    from sqlalchemy import func, select
    from app.modules.sales.models import Sale, SaleLine

    ac, sessions, (client_id, site_id, _, product_id), tokens = context
    ac.headers.update(tokens["admin"])
    payload = {
        "client_id": client_id, "site_id": site_id, "sale_date": "2026-10-01",
        "lines": [{"product_id": product_id, "quantity": 1, "unit_price": "1250.50"}],
    }
    if reference == "client":
        payload["client_id"] = 999999
    elif reference == "site":
        payload["site_id"] = 999999
    elif reference == "product":
        payload["lines"][0]["product_id"] = 999999
    else:
        response = await ac.post("/api/v1/clients", json={
            "full_name": "Other owner", "phone": "0102030406", "address": "Lyon",
        })
        assert response.status_code == 201, response.text
        other_client_id = response.json()["id"]
        response = await ac.post("/api/v1/sites", json={
            "client_id": other_client_id, "name": "Other site", "address": "Lyon",
        })
        assert response.status_code == 201, response.text
        payload["site_id"] = response.json()["id"]
    async with sessions() as db:
        before = (
            await db.scalar(select(func.count(Sale.id))),
            await db.scalar(select(func.count(SaleLine.id))),
        )
    response = await ac.post("/api/v1/sales", json=payload)
    assert response.status_code == status, response.text
    assert response.json()["detail"] == detail
    async with sessions() as db:
        assert (
            await db.scalar(select(func.count(Sale.id))),
            await db.scalar(select(func.count(SaleLine.id))),
        ) == before


@pytest.mark.parametrize("role", ["admin", "technician"])
async def test_cancelled_draft_rejects_further_transitions(context, role):
    from app.modules.sales.models import SaleStatus
    from app.modules.sales.service import SaleService

    ac, sessions, (client_id, site_id, _, product_id), tokens = context
    ac.headers.update(tokens[role])
    response = await ac.post("/api/v1/sales", json={
        "client_id": client_id, "site_id": site_id, "sale_date": "2026-10-01",
        "lines": [{"product_id": product_id, "quantity": 1, "unit_price": "1250.50"}],
    })
    assert response.status_code == 201, response.text
    sale = response.json()
    response = await ac.post(f'/api/v1/sales/{sale["id"]}/cancel')
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "CANCELLED"
    for action in ("confirm", "cancel"):
        response = await ac.post(f'/api/v1/sales/{sale["id"]}/{action}')
        assert response.status_code == 409, response.text
    async with sessions() as db:
        stored = await SaleService(db).get(sale["id"])
        assert stored.status is SaleStatus.CANCELLED
        assert len(stored.lines) == 1
        assert stored.lines[0].id == sale["lines"][0]["id"]
        assert stored.lines[0].unit_price == Decimal("1250.50")
