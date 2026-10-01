"""Contrats R3/INT-115 : catalogue isolé, identité ORM et historique commercial."""

import ast
from decimal import Decimal
from importlib.util import resolve_name
from inspect import unwrap
from unittest.mock import AsyncMock

import pytest

from tests.test_modular_bootstrap import BACKEND, ISOLATED_IMPORTS, _run_python

RETIRED_MODULES = (
    "app.models.product",
    "app.schemas.product",
    "app.repositories.product",
    "app.services.product",
    "app.api.v1.products",
    "app.modules.catalogue",
)
PRODUCT = {
    "reference": "R3-HISTORY", "name": "PAC historique", "brand": "Tervo",
    "model": "R3", "category": "PAC", "description": "Catalogue conservé",
    "characteristics": {"power_kw": 12},
}


def test_catalog_layout_and_no_retired_imports():
    package = BACKEND / "app/modules/catalog"
    assert not list((BACKEND / "app/modules/catalogue").glob("*.py"))
    assert {path.name for path in package.glob("*.py")} == {
        "__init__.py", "models.py", "schemas.py", "repository.py", "service.py", "api.py",
    }
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
def test_catalog_import_is_pure(tmp_path, module):
    _run_python(tmp_path, f"""
        from importlib import import_module
        from app.core.base import Base

        catalog = import_module("app.modules.catalog." + {module!r})
        if {module!r} == "models":
            assert set(Base.metadata.tables) == {{"product"}}
            assert {{mapper.class_ for mapper in Base.registry.mappers}} == {{catalog.Product}}
            assert catalog.Product.__module__ == catalog.__name__
        else:
            assert not Base.metadata.tables
            assert not set(Base.registry.mappers)
            product = catalog.ProductCreate(**{PRODUCT!r})
            assert product.reference == "R3-HISTORY" and product.active is True
        """, forbidden=ISOLATED_IMPORTS + RETIRED_MODULES + (
            "app.models", "app.modules.catalog.api",
            "app.modules.catalog.repository", "app.modules.catalog.service",
        ))


@pytest.mark.parametrize("order", ["catalog-first", "legacy-first"])
def test_catalog_and_legacy_orders_preserve_registry_and_relations(tmp_path, order):
    _run_python(tmp_path, f"""
        from importlib import import_module
        from sqlalchemy import inspect
        from app.core.base import Base

        first = import_module(
            "app.modules.catalog.models" if {order!r} == "catalog-first" else "app.models"
        )
        tables = dict(Base.metadata.tables)
        mappers = set(Base.registry.mappers)
        from app.model_registry import load_models
        load_models()
        assert_registry(Base)
        catalog = import_module("app.modules.catalog.models")
        legacy = import_module("app.models")
        assert first.Product is legacy.Product is catalog.Product
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
        product = inspect(catalog.Product)
        assert product.relationships["equipment"].mapper.class_ is legacy.Equipment
        equipment = inspect(legacy.Equipment).relationships["product"]
        assert equipment.mapper.class_ is catalog.Product
        assert equipment.back_populates == "equipment"
        line = inspect(legacy.SaleLine).relationships["product"]
        assert line.mapper.class_ is catalog.Product
        assert line.back_populates is None
        assert set(product.relationships.keys()) == {{"equipment"}}
        """, forbidden=ISOLATED_IMPORTS + RETIRED_MODULES)


@pytest.fixture
async def context(tmp_path, monkeypatch):
    # Vraie DB isolée, FK SQLite actives et JWT ; aucune variante PostgreSQL.
    monkeypatch.delenv("TERVO_INSTALLATION_TEST_DATABASE_URL", raising=False)
    from tests.test_installations import context as installation_context

    fixture = unwrap(installation_context)(tmp_path)
    try:
        yield await anext(fixture)
    finally:
        await fixture.aclose()


async def test_deactivation_preserves_historical_links_and_routes(context):
    from app.models.equipment import Equipment
    from app.models.sale import Sale, SaleLine
    from app.modules.catalog.models import Product
    from app.modules.customers.models import Client, Site

    ac, sessions, _, tokens = context
    ac.headers.update(tokens["admin"])
    response = await ac.post("/api/v1/clients", json={
        "full_name": "Catalogue owner", "phone": "0102030405", "address": "Paris",
    })
    assert response.status_code == 201, response.text
    owner = response.json()
    response = await ac.get(f'/api/v1/clients/{owner["id"]}')
    assert response.status_code == 200, response.text
    owner = response.json()
    response = await ac.post("/api/v1/sites", json={
        "client_id": owner["id"], "name": "Catalogue site", "address": "Paris",
    })
    assert response.status_code == 201, response.text
    site = response.json()
    response = await ac.post("/api/v1/products", json=PRODUCT)
    assert response.status_code == 201, response.text
    product = response.json()
    sale_body = {
        "client_id": owner["id"], "site_id": site["id"], "sale_date": "2026-10-01",
        "notes": "Historique R3", "lines": [{
            "product_id": product["id"], "quantity": 2, "unit_price": "1250.50",
            "description": "Prix historique",
        }],
    }
    response = await ac.post("/api/v1/sales", json=sale_body)
    assert response.status_code == 201, response.text
    sale = response.json()
    equipment_body = {
        "site_id": site["id"], "product_id": product["id"],
        "serial_number": "R3-SERIAL", "notes": "Équipement historique",
    }
    response = await ac.post("/api/v1/equipment", json=equipment_body)
    assert response.status_code == 201, response.text
    equipment = response.json()
    response = await ac.post(f'/api/v1/products/{product["id"]}/deactivate')
    assert response.status_code == 200, response.text
    inactive = response.json()
    assert inactive == {**product, "active": False, "updated_at": inactive["updated_at"]}
    async with sessions() as db:
        stored_product = await db.get(Product, product["id"])
        assert stored_product.active is False
        assert stored_product.characteristics == PRODUCT["characteristics"]
        assert (await db.get(Client, owner["id"])).full_name == owner["full_name"]
        assert (await db.get(Site, site["id"])).client_id == owner["id"]
        stored_sale = await db.get(Sale, sale["id"])
        assert (stored_sale.client_id, stored_sale.site_id) == (owner["id"], site["id"])
        line = await db.get(SaleLine, sale["lines"][0]["id"])
        assert (line.sale_id, line.product_id, line.quantity, line.unit_price, line.description) == (
            sale["id"], product["id"], 2, Decimal("1250.50"), "Prix historique",
        )
        stored_equipment = await db.get(Equipment, equipment["id"])
        assert (stored_equipment.site_id, stored_equipment.product_id,
                stored_equipment.serial_number, stored_equipment.notes) == (
            site["id"], product["id"], "R3-SERIAL", "Équipement historique",
        )
    for path, expected in (
        (f'/api/v1/products/{product["id"]}', inactive),
        (f'/api/v1/equipment/{equipment["id"]}', equipment),
        (f'/api/v1/clients/{owner["id"]}', owner),
        (f'/api/v1/sites/{site["id"]}', site),
    ):
        response = await ac.get(path)
        assert response.status_code == 200, (path, response.text)
        assert response.json() == expected
    # Sales n'expose pas de GET détail : exercer sa route historique de confirmation.
    response = await ac.post(f'/api/v1/sales/{sale["id"]}/confirm')
    assert response.status_code == 200, response.text
    confirmed = response.json()
    assert confirmed == {**sale, "status": "CONFIRMED", "updated_at": confirmed["updated_at"]}
    # Les services actuels valident l'existence, pas l'activité du produit.
    # Ne pas introduire un refus métier à l'occasion de l'extraction.
    response = await ac.post("/api/v1/sales", json=sale_body)
    assert response.status_code == 201, response.text
    assert response.json()["lines"][0]["product_id"] == product["id"]
    response = await ac.post("/api/v1/equipment", json={
        **equipment_body, "serial_number": "R3-AFTER-DEACTIVATION",
    })
    assert response.status_code == 201, response.text
    assert response.json()["product_id"] == product["id"]


async def test_product_save_rolls_back_integrity_error():
    from fastapi import HTTPException
    from sqlalchemy.exc import IntegrityError
    from app.modules.catalog.service import ProductService

    db = AsyncMock()
    service = ProductService(db)
    product = object()
    service.repo.save = AsyncMock(side_effect=IntegrityError("INSERT", {}, RuntimeError("unique")))
    with pytest.raises(HTTPException) as error:
        await service._save(product)
    assert error.value.status_code == 409
    assert error.value.detail == "Référence produit déjà utilisée"
    service.repo.save.assert_awaited_once_with(product)
    db.rollback.assert_awaited_once_with()
