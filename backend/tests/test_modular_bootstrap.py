"""Contrats R1 : bootstrap isolé et conservation exacte des snapshots R0.

Chaque scénario importe l'application dans un nouvel interpréteur, sans lifespan,
serveur HTTP ni connexion SQL. Aucun module applicatif n'est importé à la collecte.
"""

from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND = REPO_ROOT / "backend"
BASELINES = REPO_ROOT / "notes/backend/extras/refactor-monolithe-modulaire"
ISOLATED_IMPORTS = (
    "app.main",
    "app.router",
    "app.api",
    "app.core.database",
    "fastapi",
)
ROUTER_REFERENCES = (
    ("app.api.v1.imports", "router"),
    ("app.api.v1.auth", "router"),
    ("app.modules.customers.api", "clients_router"),
    ("app.api.v1.interventions", "router"),
    ("app.api.v1.dashboard", "router"),
    ("app.api.v1.checklist", "router"),
    ("app.api.v1.photos", "router"),
    ("app.api.v1.materials", "router"),
    ("app.api.v1.reports", "router"),
    ("app.api.v1.reviews", "router"),
    ("app.modules.customers.api", "sites_router"),
    ("app.modules.catalog.api", "router"),
    ("app.modules.equipment.api", "router"),
    ("app.api.v1.installations", "router"),
    ("app.modules.sales.api", "router"),
)


# Les gardes sont installées avant tout import app.*. Elles détectent aussi un
# import interdit tenté puis masqué par un try/except dans le code applicatif.
_PROCESS_GUARDS = """
import importlib.abc
import json
import sys
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import sqlalchemy
from sqlalchemy import Connection, Engine
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

forbidden_attempts = []


def assert_no_forbidden_imports():
    loaded = sorted(
        name for name in sys.modules
        if any(name == root or name.startswith(root + ".") for root in forbidden)
    )
    assert not loaded, f"Modules interdits chargés : {loaded}"
    assert not forbidden_attempts, f"Imports interdits tentés : {forbidden_attempts}"


class ImportGuard(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if any(fullname == root or fullname.startswith(root + ".") for root in forbidden):
            forbidden_attempts.append(fullname)
            raise AssertionError(f"Import interdit : {fullname}")
        return None


assert_no_forbidden_imports()
sys.meta_path.insert(0, ImportGuard())

database_attempts = []


def reject_database_io(*args, **kwargs):
    database_attempts.append("engine/connexion/SQL")
    raise AssertionError("Ce scénario ne doit créer aucun engine ni accéder à SQL")


patches = ExitStack()
for owner, name in (
    (Engine, "connect"),
    (Engine, "raw_connection"),
    (Connection, "execute"),
    (Connection, "exec_driver_sql"),
    (AsyncEngine, "connect"),
    (AsyncEngine, "raw_connection"),
    (AsyncConnection, "execute"),
    (AsyncConnection, "exec_driver_sql"),
):
    patches.enter_context(patch.object(owner, name, reject_database_io))
if block_engine:
    patches.enter_context(patch.object(Engine, "__init__", reject_database_io))
    patches.enter_context(patch.object(AsyncEngine, "__init__", reject_database_io))

expected_tables = frozenset(json.loads(metadata_baseline.read_text(encoding="utf-8")))
assert len(expected_tables) == 17


def assert_registry(Base):
    from sqlalchemy.orm import configure_mappers

    assert set(Base.metadata.tables) == expected_tables
    assert len(Base.metadata.tables) == 17
    configure_mappers()
    mappers = set(Base.registry.mappers)
    assert len(mappers) == 17
    assert all(mapper.configured for mapper in mappers)
    assert {mapper.local_table.key for mapper in mappers} == expected_tables
    assert all(
        mapper.local_table is Base.metadata.tables[mapper.local_table.key]
        for mapper in mappers
    )


result = None
"""


# Même représentation que R0 : ordre des colonnes conservé, types PostgreSQL,
# sqltext non compilé, contraintes triées par leur représentation JSON complète.
_METADATA_SERIALIZER = """
def serialize_metadata(metadata):
    from sqlalchemy.dialects import postgresql

    dialect = postgresql.dialect()
    tables = {}
    for name, table in sorted(metadata.tables.items()):
        columns = [
            {
                "name": column.name,
                "type": str(column.type.compile(dialect=dialect)),
                "nullable": column.nullable,
                "primary_key": column.primary_key,
                "server_default": (
                    str(column.server_default.arg)
                    if column.server_default is not None else None
                ),
            }
            for column in table.columns
        ]
        constraints = []
        for constraint in table.constraints:
            sqltext = getattr(constraint, "sqltext", None)
            foreign_keys = [
                {
                    "target": foreign_key.target_fullname,
                    "ondelete": foreign_key.ondelete,
                    "onupdate": foreign_key.onupdate,
                }
                for foreign_key in getattr(constraint, "elements", ())
            ]
            constraints.append({
                "kind": type(constraint).__name__,
                "name": constraint.name,
                "columns": [column.name for column in constraint.columns],
                "definition": str(sqltext) if sqltext is not None else None,
                "foreign_keys": sorted(foreign_keys, key=lambda item: item["target"]),
            })
        tables[name] = {
            "columns": columns,
            "constraints": sorted(
                constraints, key=lambda item: json.dumps(item, sort_keys=True)
            ),
        }
    return tables
"""


def _run_python(
    tmp_path: Path,
    source: str,
    *,
    forbidden: tuple[str, ...] = ISOLATED_IMPORTS,
    block_engine: bool = True,
):
    env = os.environ.copy()
    # Ne pas hériter d'un PYTHONPATH ou d'une URL PostgreSQL de la suite appelante.
    env.update(
        PYTHONPATH=str(BACKEND),
        PYTHONDONTWRITEBYTECODE="1",
        PYTHONOPTIMIZE="0",
        DATABASE_URL="sqlite:///./tervo.db",
        UPLOAD_DIR=str(tmp_path / "uploads"),
        APP_NAME="Tervo",
        APP_VERSION="0.1.0",
        API_V1_PREFIX="/api/v1",
        UPLOAD_URL="/uploads",
    )
    for name in tuple(env):
        if name.startswith("TERVO_") and ("DATABASE" in name or "MIGRATION" in name):
            env.pop(name)

    output = tmp_path / "result.json"
    script = (
        f"forbidden = {forbidden!r}\n"
        f"block_engine = {block_engine!r}\n"
        "from pathlib import Path\n"
        f"metadata_baseline = Path({str(BASELINES / 'R0-metadata.json')!r})\n"
        + _PROCESS_GUARDS
        + textwrap.dedent(source)
        + "\nassert_no_forbidden_imports()\n"
        + "assert not database_attempts, database_attempts\n"
        + "Path(sys.argv[1]).write_text(json.dumps(result, sort_keys=True), encoding='utf-8')\n"
    )
    try:
        completed = subprocess.run(
            [sys.executable, "-c", script, str(output)],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        pytest.fail(
            f"Bootstrap dépassant 20 s.\nstdout:\n{exc.stdout}\nstderr:\n{exc.stderr}",
            pytrace=False,
        )
    assert completed.returncode == 0, (
        f"Bootstrap échoué (code {completed.returncode}).\n"
        f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
    )
    return json.loads(output.read_text(encoding="utf-8"))


def test_core_base_is_pure_in_fresh_process(tmp_path):
    _run_python(
        tmp_path,
        """
        from sqlalchemy.orm import DeclarativeBase
        from app.core.base import Base

        assert issubclass(Base, DeclarativeBase)
        assert not Base.metadata.tables
        assert not set(Base.registry.mappers)
        """,
        forbidden=ISOLATED_IMPORTS + ("app.models",),
    )


def test_registry_import_does_not_eagerly_load_models(tmp_path):
    _run_python(
        tmp_path,
        """
        from app.model_registry import load_models
        from app.core.base import Base

        assert callable(load_models)
        assert not Base.metadata.tables
        assert not set(Base.registry.mappers)
        """,
        forbidden=ISOLATED_IMPORTS + ("app.models",),
    )


def test_load_models_registers_exact_r0_tables_without_web_or_engine(tmp_path):
    _run_python(
        tmp_path,
        """
        from app.core.base import Base
        from app.model_registry import load_models

        assert not Base.metadata.tables
        load_models()
        assert_registry(Base)
        """,
    )


def test_load_models_is_complete_without_legacy_package_reexports(tmp_path):
    _run_python(
        tmp_path,
        f"""
        from types import ModuleType
        import app
        from app.core.base import Base

        assert "app.models" not in sys.modules
        assert not Base.metadata.tables
        assert not set(Base.registry.mappers)
        # Garder les vrais sous-modules, sans exécuter le __init__ legacy qui
        # pourrait charger un modèle oublié par le registre explicite.
        models_package = ModuleType("app.models")
        models_package.__package__ = "app.models"
        models_package.__path__ = [{str(BACKEND / 'app/models')!r}]
        sys.modules["app.models"] = models_package
        app.models = models_package

        from app.model_registry import load_models

        assert not Base.metadata.tables
        load_models()
        assert_registry(Base)
        metadata = Base.metadata
        registry = Base.registry
        tables = dict(metadata.tables)
        mappers = set(registry.mappers)
        for _ in range(3):
            load_models()
            assert_registry(Base)
            assert Base.metadata is metadata
            assert Base.registry is registry
            assert all(metadata.tables[name] is table for name, table in tables.items())
            assert set(registry.mappers) == mappers
        assert sys.modules["app.models"] is models_package
        assert not hasattr(models_package, "Base")
        assert not hasattr(models_package, "Client")
        assert not hasattr(models_package, "Site")
        from app.modules.customers.models import Client, Site
        assert Client.__table__ is tables["client"]
        assert Site.__table__ is tables["site"]
        """,
    )


def test_load_models_is_idempotent_for_tables_and_mappers(tmp_path):
    _run_python(
        tmp_path,
        """
        from app.core.base import Base
        from app.model_registry import load_models

        load_models()
        assert_registry(Base)
        metadata = Base.metadata
        registry = Base.registry
        tables = dict(metadata.tables)
        mappers = set(registry.mappers)
        for _ in range(3):
            load_models()
            assert Base.metadata is metadata
            assert Base.registry is registry
            assert_registry(Base)
            assert set(metadata.tables) == set(tables)
            assert all(metadata.tables[name] is table for name, table in tables.items())
            assert set(registry.mappers) == mappers
        """,
    )


def test_legacy_base_exports_are_the_core_base(tmp_path):
    _run_python(
        tmp_path,
        """
        from app.core.base import Base
        from app.models import Base as package_base
        from app.models.base import Base as compatibility_base

        assert package_base is compatibility_base is Base
        assert_registry(Base)
        """,
    )


@pytest.mark.parametrize("order", ["legacy-first", "registry-first"])
def test_legacy_and_registry_import_orders_share_one_registry(tmp_path, order):
    _run_python(
        tmp_path,
        f"""
        import importlib
        from app.core.base import Base

        if {order!r} == "legacy-first":
            legacy = importlib.import_module("app.models")
        else:
            from app.model_registry import load_models
            load_models()

        assert_registry(Base)
        tables = dict(Base.metadata.tables)
        mappers = set(Base.registry.mappers)
        from app.model_registry import load_models
        load_models()
        legacy = importlib.import_module("app.models")
        compatibility = importlib.import_module("app.models.base")
        load_models()

        from app.modules.customers.models import Client, Site
        assert legacy.Base is compatibility.Base is Base
        assert legacy.Client is Client
        assert legacy.Site is Site
        assert_registry(Base)
        assert all(Base.metadata.tables[name] is table for name, table in tables.items())
        assert set(Base.registry.mappers) == mappers
        assert all(
            getattr(legacy, mapper.class_.__name__) is mapper.class_
            for mapper in mappers
        )
        """,
    )


def test_metadata_matches_r0_exactly(tmp_path):
    actual = _run_python(
        tmp_path,
        _METADATA_SERIALIZER
        + """
from app.core.base import Base
from app.model_registry import load_models

load_models()
assert_registry(Base)
result = serialize_metadata(Base.metadata)
""",
    )
    expected = json.loads((BASELINES / "R0-metadata.json").read_text(encoding="utf-8"))
    assert actual == expected


def test_openapi_matches_r0_exactly_without_startup_or_sql(tmp_path):
    actual = _run_python(
        tmp_path,
        """
        from app.main import app
        from app.core.base import Base

        assert_registry(Base)
        result = app.openapi()
        """,
        forbidden=(),
        block_engine=False,
    )
    expected = json.loads((BASELINES / "R0-openapi.json").read_text(encoding="utf-8"))
    assert actual == expected


def test_api_router_aggregates_exact_legacy_routes_in_order(tmp_path):
    _run_python(
        tmp_path,
        f"""
        from importlib import import_module
        from fastapi import APIRouter, routing
        from fastapi.routing import APIRoute
        from app.router import api_router

        assert isinstance(api_router, APIRouter)

        def route_signature(route, context):
            assert isinstance(route, APIRoute), type(route)
            effective = context if context is not None else route
            return (
                effective.path,
                tuple(sorted(effective.methods)),
                effective.endpoint,
                effective.name,
                effective.operation_id,
                effective.include_in_schema,
            )

        # Un APIRouter témoin laisse FastAPI appliquer ses règles de copie et
        # d'inclusion, y compris sur les versions à inclusion différée.
        expected_router = APIRouter()
        for module, attribute in {ROUTER_REFERENCES!r}:
            expected_router.include_router(getattr(import_module(module), attribute))

        customers = import_module("app.modules.customers.api")
        assert customers.clients_router.prefix == "/clients"
        assert customers.clients_router.tags == ["clients"]
        assert customers.sites_router.prefix == "/sites"
        assert customers.sites_router.tags == ["sites"]

        def signatures(router):
            # FastAPI 0.138 conserve des inclusions différées dans .routes.
            # Utiliser son itérateur de contextes effectifs si disponible.
            iterator = getattr(routing, "_iter_routes_with_context", None)
            routes = (
                iterator(router.routes) if iterator is not None
                else ((route, None) for route in router.routes)
            )
            return [route_signature(route, context) for route, context in routes]

        assert signatures(api_router) == signatures(expected_router)
        """,
        forbidden=("app.main",),
        block_engine=False,
    )


@pytest.mark.parametrize(
    ("entrypoint", "function_name", "barrier"),
    [
        ("app/main.py", None, "include_router"),
        ("alembic/env.py", None, "target_metadata"),
        ("app/seed.py", "seed", "create_all"),
    ],
    ids=["main", "alembic", "seed"],
)
def test_entrypoints_explicitly_load_models_before_use(entrypoint, function_name, barrier):
    # Analyse source uniquement : ne pas importer env.py ni exécuter le seed.
    path = BACKEND / entrypoint
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    registry_imports = [
        node for node in tree.body
        if isinstance(node, ast.ImportFrom)
        and node.module == "app.model_registry"
        and any(
            alias.name == "load_models" and alias.asname in (None, "load_models")
            for alias in node.names
        )
    ]
    assert registry_imports, f"{entrypoint} doit importer le registre explicite"

    base_imports = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and any(alias.name == "Base" for alias in node.names)
    ]
    assert all(node.module == "app.core.base" for node in base_imports), (
        f"{entrypoint} ne doit pas importer une Base legacy"
    )
    if barrier != "include_router":
        assert base_imports, f"{entrypoint} doit importer Base depuis app.core.base"

    statements = tree.body
    if function_name is not None:
        functions = [
            node for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == function_name
        ]
        assert len(functions) == 1
        statements = functions[0].body

    # Un appel direct dans ce corps ne peut pas être caché dans une fonction
    # inutilisée ou une branche conditionnelle qui ne s'exécute jamais.
    loads = [
        (index, statement.value)
        for index, statement in enumerate(statements)
        if isinstance(statement, ast.Expr)
        and isinstance(statement.value, ast.Call)
        and isinstance(statement.value.func, ast.Name)
        and statement.value.func.id == "load_models"
    ]
    assert loads, f"{entrypoint} doit appeler explicitement load_models()"
    load_index, load_call = loads[0]
    assert not load_call.args and not load_call.keywords
    assert any(node.lineno < load_call.lineno for node in registry_imports)

    barriers = []
    for index, statement in enumerate(statements):
        if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        if barrier == "target_metadata":
            if isinstance(statement, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == "target_metadata"
                for target in statement.targets
            ):
                assert ast.unparse(statement.value) == "Base.metadata"
                barriers.append(index)
        else:
            for node in ast.walk(statement):
                if barrier == "include_router":
                    matches = (
                        isinstance(node, ast.Call)
                        and isinstance(node.func, ast.Attribute)
                        and ast.unparse(node.func) == "app.include_router"
                    )
                else:
                    # create_all peut être appelé directement ou passé à run_sync.
                    matches = (
                        isinstance(node, ast.Attribute)
                        and ast.unparse(node) == "Base.metadata.create_all"
                    )
                if matches:
                    barriers.append(index)
    assert barriers, f"{entrypoint} : usage attendu absent ({barrier})"
    assert all(load_index < index for index in barriers), (
        f"{entrypoint} doit appeler load_models() avant {barrier}"
    )
