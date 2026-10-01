"""R9/INT-121: import-domain boundaries, not the functional pack comparison."""

import ast
from importlib.util import resolve_name
import os
import subprocess
import sys

import pytest

from tests.test_modular_bootstrap import BACKEND, ISOLATED_IMPORTS, _run_python


RETIRED_MODULES = (
    "app.importers",
    "app.models.import_batch",
    "app.schemas.imports",
    "app.services.import_planner",
    "app.services.import_service",
    "app.api.v1.imports",
)
MODEL_NAMES = ("ImportBatch", "ImportRecord", "ImportReference", "ImportError")
PIPELINE_FILES = {
    "__init__.py", "excel_reader.py", "format_detector.py", "ingestion.py",
    "normalizer.py", "validators.py", "matcher.py", "multi_matcher.py", "report.py",
}


def test_imports_layout_and_cutover():
    package = BACKEND / "app/modules/imports"
    assert {p.name for p in package.iterdir() if p.name != "__pycache__"} == {
        "__init__.py", "models.py", "schemas.py", "planner.py", "service.py", "api.py",
        "pipeline",
    }
    assert {p.name for p in (package / "pipeline").glob("*.py")} == PIPELINE_FILES
    tree = ast.parse((package / "__init__.py").read_text(encoding="utf-8"))
    assert len(tree.body) == 1 and ast.get_docstring(tree) is not None
    old_paths = [
        "app/importers/__init__.py", "app/models/import_batch.py", "app/schemas/imports.py",
        "app/services/import_planner.py", "app/services/import_service.py", "app/api/v1/imports.py",
        *(f"app/importers/{name}" for name in PIPELINE_FILES - {"__init__.py"}),
    ]
    assert not [path for path in old_paths if (BACKEND / path).exists()]
    violations = []
    for root in (BACKEND / "app", BACKEND / "tests"):
        for path in root.rglob("*.py"):
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if isinstance(node, ast.Import):
                    imports = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    if node.level:
                        module = resolve_name(
                            "." * node.level + module,
                            ".".join(path.parent.relative_to(BACKEND).parts),
                        )
                    imports = [module, *(module + "." + alias.name for alias in node.names)]
                else:
                    continue
                if any(name == old or name.startswith(old + ".")
                       for name in imports for old in RETIRED_MODULES):
                    violations.append(f"{path.relative_to(BACKEND)}:{node.lineno}")
    assert not violations, violations


def test_imports_root_init_is_pure(tmp_path):
    _run_python(tmp_path, """
        from importlib import import_module
        from app.core.base import Base
        import_module("app.modules.imports")
        assert not Base.metadata.tables
        assert not list(Base.registry.mappers)
        """, forbidden=ISOLATED_IMPORTS + RETIRED_MODULES + (
            "app.models", "app.modules.imports.models", "app.modules.imports.schemas",
            "app.modules.imports.planner", "app.modules.imports.service",
            "app.modules.imports.api", "app.modules.imports.pipeline",
        ))


def test_low_level_pipeline_stays_framework_and_database_free(tmp_path):
    # This subprocess deliberately does not preload SQLAlchemy like _run_python.
    source = """
import importlib.abc
import sys
class Guard(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in {"fastapi", "sqlalchemy", "alembic", "asyncpg", "aiosqlite"}:
            raise AssertionError(fullname)
        if fullname.startswith(("app.core", "app.models", "app.api", "app.services",
                                "app.repositories", "app.schemas", "app.main", "app.router")):
            raise AssertionError(fullname)
sys.meta_path.insert(0, Guard())
from app.modules.imports import pipeline
assert pipeline.AUTO_MATCH_THRESHOLD == 95.0
assert pipeline.HUMAN_REVIEW_THRESHOLD == 80.0
assert pipeline.DEFAULT_BATCH_SIZE == 500
assert {"ExcelReader", "Normalizer", "Validator", "ClientMatcher", "ImportReport"} <= set(pipeline.__all__)
assert "app.modules.imports.planner" not in sys.modules
assert "app.modules.imports.service" not in sys.modules
assert "app.modules.imports.models" not in sys.modules
assert "app.modules.imports.api" not in sys.modules
"""
    env = {key: value for key, value in os.environ.items() if not key.startswith("TERVO_")}
    env.update(PYTHONPATH=str(BACKEND), PYTHONDONTWRITEBYTECODE="1")
    result = subprocess.run(
        [sys.executable, "-c", source], cwd=tmp_path, env=env,
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("module", ["models", "schemas"])
def test_imports_models_and_schemas_without_api_or_database_io(tmp_path, module):
    _run_python(tmp_path, f"""
        from importlib import import_module
        from app.core.base import Base
        imported = import_module("app.modules.imports." + {module!r})
        if {module!r} == "models":
            assert set(Base.metadata.tables) == {{
                "import_batch", "import_record", "import_reference", "import_error",
            }}
            assert {{mapper.class_ for mapper in Base.registry.mappers}} == {{
                getattr(imported, name) for name in {MODEL_NAMES!r}
            }}
        else:
            assert not Base.metadata.tables
        """, forbidden=ISOLATED_IMPORTS + RETIRED_MODULES + (
            "app.models", "app.modules.imports.api", "app.modules.imports.service",
            "app.modules.imports.planner",
        ))


@pytest.mark.parametrize("order", ["imports-first", "legacy-first"])
def test_imports_registry_identity_and_journal_constraints(tmp_path, order):
    _run_python(tmp_path, f"""
        from importlib import import_module
        from app.core.base import Base
        first = import_module(
            "app.modules.imports.models" if {order!r} == "imports-first" else "app.models"
        )
        partial = dict(Base.metadata.tables)
        from app.model_registry import load_models
        load_models()
        assert_registry(Base)
        models = import_module("app.modules.imports.models")
        legacy = import_module("app.models")
        assert models.Base is legacy.Base is Base
        for name in {MODEL_NAMES!r}:
            assert getattr(first, name) is getattr(legacy, name) is getattr(models, name)
        complete = set(Base.registry.mappers)
        load_models()
        assert_registry(Base)
        assert set(Base.registry.mappers) == complete
        assert all(Base.metadata.tables[name] is table for name, table in partial.items())
        for table in Base.metadata.tables.values():
            for fk in table.foreign_keys:
                assert fk.column.table is Base.metadata.tables[fk.column.table.key]
        assert models.ImportBatch.__table__.c.execution_slot.unique
        expected = {{
            "import_batch": ("source_namespace", "file_hash"),
            "import_record": ("import_batch_id", "row_key"),
            "import_reference": ("source_namespace", "entity_type", "source_id"),
        }}
        from sqlalchemy import UniqueConstraint
        for table, columns in expected.items():
            assert any(isinstance(c, UniqueConstraint) and tuple(c.columns.keys()) == columns
                       for c in Base.metadata.tables[table].constraints)
        """, forbidden=ISOLATED_IMPORTS + RETIRED_MODULES)


def test_six_admin_import_routes_are_composed_once(tmp_path):
    _run_python(tmp_path, """
        from fastapi import routing
        from fastapi.routing import APIRoute
        from app.main import app
        from app.modules.imports.api import router
        iterator = getattr(routing, "_iter_routes_with_context", None)
        routes = iterator(app.routes) if iterator else ((route, None) for route in app.routes)
        effective = [context if context is not None else route
                     for route, context in routes if isinstance(route, APIRoute)]
        local = [route for route in router.routes if isinstance(route, APIRoute)]
        assert len(local) == 6
        assert router.prefix == "/admin/import"
        assert router.tags == ["admin-import"]
        for route in local:
            found = [candidate for candidate in effective
                     if candidate.path == "/api/v1" + route.path
                     and candidate.methods == route.methods]
            assert len(found) == 1
            assert found[0].endpoint is route.endpoint
        """, forbidden=RETIRED_MODULES, block_engine=False)
