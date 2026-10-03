"""R7/INT-119 : frontières terrain et consommateurs après cutover, sans feature."""

import ast
from importlib.util import resolve_name
from inspect import unwrap
from pathlib import Path

import pytest

from tests.test_modular_bootstrap import BACKEND, ISOLATED_IMPORTS, _run_python


LAYOUT = {
    "models": ("intervention", "checklist", "checklist_item", "photo", "material_usage", "review"),
    "schemas": ("intervention", "checklist", "review"),
    "repositories": ("intervention", "checklist", "photo", "material", "review"),
    "services": ("intervention", "checklist", "photo", "material", "review"),
    "api": ("interventions", "checklist", "photos", "materials", "reviews"),
}
PACKAGE = "app.modules.interventions"
RETIRED_MODULES = tuple(
    f"app.{'api.v1' if layer == 'api' else layer}.{name}"
    for layer, names in LAYOUT.items() for name in names
)
MODEL_NAMES = {
    "intervention": "Intervention",
    "checklist_item": "ChecklistItem",
    "photo": "Photo",
    "material_usage": "MaterialUsage",
    "review": "Review",
}


def test_interventions_layout_and_cutover_imports():
    package = BACKEND / "app/modules/interventions"
    assert {p.name for p in package.iterdir() if not p.name.startswith(".")
            and p.name != "__pycache__"} == {"__init__.py", *LAYOUT}
    for layer, names in LAYOUT.items():
        assert {p.name for p in (package / layer).glob("*.py")} == {
            "__init__.py", *(name + ".py" for name in names),
        }
    for path in [package / "__init__.py", *(
        package / layer / "__init__.py" for layer in LAYOUT
    )]:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        assert len(tree.body) == 1 and ast.get_docstring(tree) is not None, path
    assert len(RETIRED_MODULES) == 24
    assert not [name for name in RETIRED_MODULES
                if (BACKEND / (name.replace(".", "/") + ".py")).exists()]
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
                    modules = [module, *(module + "." + a.name for a in node.names)]
                else:
                    continue
                if any(name == old or name.startswith(old + ".")
                       for name in modules for old in RETIRED_MODULES):
                    violations.append(f"{path.relative_to(BACKEND)}:{node.lineno}")
    assert not violations, "Imports legacy restants : " + ", ".join(violations)


@pytest.mark.parametrize(
    ("entrypoint", "layer"),
    [("app/model_registry.py", "models"), ("app/router.py", "api")],
)
def test_bootstrap_imports_explicit_terrain_leaves(entrypoint, layer):
    tree = ast.parse((BACKEND / entrypoint).read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            imported.add(module)
            imported.update(module + "." + alias.name for alias in node.names)
    assert {f"{PACKAGE}.{layer}.{name}" for name in LAYOUT[layer]} <= imported


@pytest.mark.parametrize("subpackage", ["", *LAYOUT])
def test_interventions_packages_are_pure(tmp_path, subpackage):
    name = PACKAGE + ("." + subpackage if subpackage else "")
    leaves = tuple(f"{PACKAGE}.{layer}.{leaf}"
                   for layer, names in LAYOUT.items() for leaf in names)
    _run_python(tmp_path, f"""
        from importlib import import_module
        from app.core.base import Base
        import_module({name!r})
        assert not Base.metadata.tables
        assert not list(Base.registry.mappers)
        """, forbidden=ISOLATED_IMPORTS + RETIRED_MODULES + ("app.models",) + leaves)


@pytest.mark.parametrize("order", ["terrain-first", "registry-first"])
def test_interventions_identity_base_and_relations(tmp_path, order):
    _run_python(tmp_path, f"""
        from importlib import import_module
        from sqlalchemy import inspect
        from app.core.base import Base
        names = {MODEL_NAMES!r}
        from app.model_registry import load_models
        if {order!r} == "terrain-first":
            for name in names:
                import_module({PACKAGE!r} + ".models." + name)
        else:
            load_models()
        tables = dict(Base.metadata.tables)
        mappers = set(Base.registry.mappers)
        from app.model_registry import load_models
        load_models()
        assert_registry(Base)
        classes = {{}}
        for module_name, class_name in names.items():
            module = import_module({PACKAGE!r} + ".models." + module_name)
            cls = getattr(module, class_name)
            classes[class_name] = cls
            assert inspect(cls) is next(
                mapper for mapper in Base.registry.mappers if mapper.class_ is cls
            )
            assert cls.__module__ == module.__name__
            assert module.Base is Base
            assert cls.metadata is Base.metadata
        assert mappers <= set(Base.registry.mappers)
        assert all(Base.metadata.tables[name] is table for name, table in tables.items())
        complete = set(Base.registry.mappers)
        load_models()
        assert_registry(Base)
        assert set(Base.registry.mappers) == complete
        intervention = classes["Intervention"]
        from app.modules.interventions.models.checklist import (
            ChecklistTemplate, InterventionChecklist,
        )
        for cls in (ChecklistTemplate, InterventionChecklist):
            assert cls.metadata is Base.metadata
            assert cls.__module__ == {PACKAGE!r} + ".models.checklist"
        snapshot = inspect(intervention).relationships["checklist"]
        assert snapshot.mapper.class_ is InterventionChecklist
        assert not snapshot.uselist
        assert InterventionChecklist.__table__.c.intervention_id.unique
        assert inspect(InterventionChecklist).relationships["intervention"].mapper.class_ is intervention
        assert inspect(InterventionChecklist).relationships["items"].mapper.class_ is classes["ChecklistItem"]
        assert inspect(classes["ChecklistItem"]).relationships["checklist"].mapper.class_ is InterventionChecklist
        assert inspect(intervention).relationships["checklist_items"].viewonly
        for relation, target in (
            ("checklist_items", "ChecklistItem"), ("photos", "Photo"),
            ("materials", "MaterialUsage"), ("review", "Review"),
        ):
            assert inspect(intervention).relationships[relation].mapper.class_ is classes[target]
            if relation != "checklist_items":
                assert inspect(classes[target]).relationships["intervention"].mapper.class_ is intervention
        from app.modules.customers.models import Site
        from app.modules.equipment.models import Equipment
        from app.modules.identity.models import User
        for relation, target in (("site", Site), ("equipment", Equipment), ("technician", User)):
            assert inspect(intervention).relationships[relation].mapper.class_ is target
            assert inspect(target).relationships["interventions"].mapper.class_ is intervention
        assert not inspect(intervention).relationships["review"].uselist
        assert classes["Review"].__table__.c.intervention_id.unique
        for table in Base.metadata.tables.values():
            for fk in table.foreign_keys:
                assert fk.column.table is Base.metadata.tables[fk.column.table.key]
        """, forbidden=ISOLATED_IMPORTS + RETIRED_MODULES)


def test_five_terrain_routers_are_composed_once(tmp_path):
    _run_python(tmp_path, f"""
        from importlib import import_module
        from fastapi import routing
        from fastapi.routing import APIRoute
        from app.main import app
        iterator = getattr(routing, "_iter_routes_with_context", None)
        routes = iterator(app.routes) if iterator else ((r, None) for r in app.routes)
        effective = [context if context is not None else route
                     for route, context in routes if isinstance(route, APIRoute)]
        for name in {LAYOUT["api"]!r}:
            router = import_module({PACKAGE!r} + ".api." + name).router
            local = [r for r in router.routes if isinstance(r, APIRoute)]
            assert local, name
            for route in local:
                matches = [r for r in effective
                           if r.path == "/api/v1" + route.path and r.methods == route.methods]
                assert len(matches) == 1, (name, route.path)
                assert matches[0].endpoint is route.endpoint
        """, forbidden=RETIRED_MODULES, block_engine=False)


def test_existing_schema_contracts():
    from pydantic import ValidationError
    from app.modules.interventions.schemas.intervention import (
        ChecklistItemUpdate, InterventionCreate, InterventionUpdate, MaterialCreate,
        PhotoRef,
    )
    from app.modules.interventions.schemas.review import ReviewSubmitRequest

    body = InterventionCreate(site_id=1, title="Terrain", scheduled_date="2026-09-28")
    assert body.equipment_id is None and body.priority == "normale"
    assert body.under_warranty is False
    assert InterventionUpdate(equipment_id=None).model_dump(exclude_unset=True) == {
        "equipment_id": None,
    }
    # Priority remains historical; material inputs now carry a numeric quantity and unit.
    assert InterventionCreate(**{**body.model_dump(), "priority": "libre"}).priority == "libre"
    assert MaterialCreate(designation="Joint", quantity=2, unit="m").quantity == 2
    assert ChecklistItemUpdate(result="OK").comment is None
    with pytest.raises(ValidationError):
        ChecklistItemUpdate(checked=True)
    assert PhotoRef(id=1, usage="BEFORE", file_url="/uploads/photos/a.jpg").thumbnail_url is None
    for payload in ({"rating": 0}, {"rating": 6}, {"rating": 5, "comment": "x" * 2001}):
        with pytest.raises(ValidationError):
            ReviewSubmitRequest(**payload)
    with pytest.raises(ValidationError):
        InterventionCreate(**{**body.model_dump(), "equipment_id": 0})


@pytest.fixture
async def context(tmp_path, monkeypatch):
    # Reuse real JWT/users/SQLite FK fixture, never its optional PostgreSQL schema.
    monkeypatch.delenv("TERVO_INSTALLATION_TEST_DATABASE_URL", raising=False)
    from tests.test_installations import context as installation_context

    fixture = unwrap(installation_context)(tmp_path)
    try:
        yield await anext(fixture)
    finally:
        await fixture.aclose()


async def _create_terrain(context):
    ac, _, (_, site_id, _, _), _ = context
    response = await ac.post("/api/v1/interventions", json={
        "site_id": site_id, "title": "Terrain R7", "scheduled_date": "2026-09-28",
    })
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def test_photo_files_and_detail_consumer_survive_cutover(context, tmp_path, monkeypatch):
    from io import BytesIO
    from PIL import Image
    from starlette.datastructures import Headers, UploadFile
    from app.config import settings
    from app.modules.interventions.models.photo import Photo
    from app.modules.interventions.services.photo import PhotoService

    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path / "uploads"))
    intervention_id = await _create_terrain(context)
    ac, sessions, _, _ = context
    content = BytesIO()
    Image.new("RGB", (640, 480), "blue").save(content, "JPEG")
    original = content.getvalue()
    async with sessions() as db:
        result = await PhotoService(db).upload_photo(
            intervention_id,
            UploadFile(filename="terrain.jpg", file=BytesIO(original),
                       headers=Headers({"content-type": "image/jpeg"})),
            "BEFORE",
        )
        result = result.model_dump()
        photo = await db.get(Photo, result["id"])
        paths = [Path(photo.file_path), Path(photo.thumbnail_path)]
        assert paths[0].read_bytes() == original
        with Image.open(paths[1]) as thumbnail:
            assert max(thumbnail.size) <= 300
        assert photo.file_url == result["file_url"]
        assert photo.thumbnail_url == result["thumbnail_url"]
    response = await ac.get(f"/api/v1/interventions/{intervention_id}")
    assert response.status_code == 200, response.text
    attached = response.json()["photos"]
    assert len(attached) == 1
    assert attached[0]["id"] == result["id"]
    assert attached[0]["file_url"] == result["file_url"]
    assert attached[0]["thumbnail_url"] == result["thumbnail_url"]
    assert all(path.is_file() for path in paths)


async def test_checklist_material_completion_public_review_and_report(context):
    from app.modules.interventions.schemas.intervention import MaterialCreate
    from app.modules.interventions.services.checklist import ChecklistService
    from app.modules.interventions.services.material import MaterialService

    intervention_id = await _create_terrain(context)
    ac, sessions, _, _ = context
    url = f"/api/v1/interventions/{intervention_id}"
    response = await ac.put(url + "/start")
    assert response.status_code == 200, response.text
    async with sessions() as db:
        checklist = ChecklistService(db)
        items = await checklist.get_items(intervention_id)
        assert len(items) == 5
        for item in items:
            patched = await ac.patch(
                f"/api/v1/checklist-items/{item.id}",
                json={"result": "OK", "comment": "R7"},
            )
            assert patched.status_code == 200, patched.text
            assert patched.json()["result"] == "OK"
            assert patched.json()["comment"] == "R7"
        assert (await checklist.validate_all_checked(intervention_id))["is_valid"]
        material = await MaterialService(db).create_material(
            intervention_id, MaterialCreate(designation="Joint R7", quantity=2, unit="m"),
        )
    response = await ac.put(url + "/complete", json={"result": "RESOLVED", "observations": "Terrain conservé"})
    assert response.status_code == 200, response.text
    complete = response.json()
    assert complete["status"] == "COMPLETED"
    response = await ac.get(url)
    assert response.status_code == 200, response.text
    detail = response.json()
    assert len(detail["checklist_items"]) == 5
    assert all(item["result"] == "OK" and item["comment"] == "R7"
               for item in detail["checklist_items"])
    assert detail["materials"] == [material.model_dump()]
    response = await ac.get(complete["report_url"])
    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
    # Public review intentionally remains usable without a JWT.
    ac.headers.pop("Authorization", None)
    review_url = "/api/v1/review/" + complete["review_share_token"]
    response = await ac.get(review_url)
    assert response.status_code == 200, response.text
    assert response.json()["intervention"]["title"] == "Terrain R7"
    assert response.json()["already_reviewed"] is False
    response = await ac.post(review_url + "/submit", json={
        "rating": 4, "comment": "Conservé R7", "reviewer_name": "Client",
    })
    assert response.status_code == 200, response.text
    assert (await ac.get(review_url)).json()["already_reviewed"] is True
