"""Explicit INT-104 delta; R0 artifacts remain immutable historical evidence."""

from copy import deepcopy

ADDED_TABLES = {"checklist_template", "intervention_checklist"}


def assert_metadata_contract(actual, historical):
    assert set(actual) == set(historical) | ADDED_TABLES
    for name in historical:
        if name != "checklist_item":
            assert actual[name] == historical[name], name
    expected_columns = {
        "checklist_template": {
            "id": ("INTEGER", False), "name": ("VARCHAR(255)", False),
            "intervention_type": ("VARCHAR(100)", False),
            "version": ("INTEGER", False), "active": ("BOOLEAN", False),
            "items": ("JSON", False),
        },
        "intervention_checklist": {
            "id": ("INTEGER", False), "intervention_id": ("INTEGER", False),
            "template_id": ("INTEGER", True), "template_name": ("VARCHAR(255)", False),
            "template_version": ("INTEGER", False),
            "created_at": ("TIMESTAMP WITHOUT TIME ZONE", False),
        },
        "checklist_item": {
            "id": ("INTEGER", False), "intervention_checklist_id": ("INTEGER", False),
            "category": ("VARCHAR(20)", False), "label": ("VARCHAR(255)", False),
            "position": ("INTEGER", False), "result": ("VARCHAR(100)", True),
            "comment": ("TEXT", True),
            "completed_at": ("TIMESTAMP WITHOUT TIME ZONE", True),
        },
    }
    for name, expected in expected_columns.items():
        columns = {column["name"]: column for column in actual[name]["columns"]}
        assert set(columns) == set(expected), name
        for key, (kind, nullable) in expected.items():
            assert columns[key]["type"] == kind, (name, key)
            assert columns[key]["nullable"] is nullable, (name, key)
            assert columns[key]["primary_key"] is (key == "id"), (name, key)
    old_columns = {column["name"]: column for column in historical["checklist_item"]["columns"]}
    for column in actual["checklist_item"]["columns"]:
        if column["name"] in {"id", "category", "label", "position"}:
            assert column == old_columns[column["name"]]
    expected_fks = {
        "checklist_template": set(),
        "intervention_checklist": {
            ("intervention_id", "intervention.id", "CASCADE"),
            ("template_id", "checklist_template.id", "RESTRICT"),
        },
        "checklist_item": {
            ("intervention_checklist_id", "intervention_checklist.id", "CASCADE"),
        },
    }
    for name, expected in expected_fks.items():
        constraints = actual[name]["constraints"]
        assert all(c["kind"] in {"PrimaryKeyConstraint", "ForeignKeyConstraint",
                                 "UniqueConstraint", "CheckConstraint"} for c in constraints), name
        checks = [(c["name"], c["definition"]) for c in constraints if c["kind"] == "CheckConstraint"]
        assert checks == (
            [("ck_intervention_checklist_template_version", "template_version >= 1")]
            if name == "intervention_checklist" else
            [("ck_checklist_template_version", "version >= 1")]
            if name == "checklist_template" else []
        ), name
        primary_keys = [c["columns"] for c in constraints if c["kind"] == "PrimaryKeyConstraint"]
        assert primary_keys == [["id"]], name
        assert all(fk["onupdate"] is None for c in constraints for fk in c["foreign_keys"])
        fks = {
            (constraint["columns"][0], fk["target"], fk["ondelete"])
            for constraint in constraints for fk in constraint["foreign_keys"]
        }
        assert fks == expected, name
        unique = {tuple(c["columns"]) for c in constraints if c["kind"] == "UniqueConstraint"}
        assert unique == ({("intervention_id",)} if name == "intervention_checklist" else set())


def project_import_database(database):
    """Project the historical replay after verifying its explicit INT-104 extension."""
    assert ADDED_TABLES <= database.keys()
    for name in {"checklist_template", "checklist_item"}:
        assert database[name] == [], f"Import unexpectedly populated {name}"
    snapshots = database["intervention_checklist"]
    intervention_ids = {row["id"] for row in database["intervention"]}
    assert len(snapshots) == len(intervention_ids)
    assert {row["intervention_id"] for row in snapshots} == intervention_ids
    for row in snapshots:
        assert row["template_id"] is None
        assert row["template_name"] == "Checklist historique"
        assert row["template_version"] == 1
        assert row["created_at"] is not None
    return {name: rows for name, rows in database.items() if name not in ADDED_TABLES}


def assert_openapi_contract(actual, historical):
    prefix = "/api/v1"
    old_paths = {path for path in historical["paths"] if "/checklist" in path}
    allowed_paths = {
        prefix + "/checklist-templates": {"get", "post"},
        prefix + "/checklist-templates/{template_id}": {"patch"},
        prefix + "/checklist-items/{item_id}": {"patch"},
        prefix + "/interventions/{intervention_id}/checklist": {"get"},
    }
    assert set(actual["paths"]) == (set(historical["paths"]) - old_paths) | set(allowed_paths)
    for path, methods in allowed_paths.items():
        assert set(actual["paths"][path]) == methods, path
        for method in methods:
            assert actual["paths"][path][method]["responses"]
    old_schemas = historical["components"]["schemas"]
    schemas = actual["components"]["schemas"]

    def resolve(schema):
        if "$ref" in schema:
            return schemas[schema["$ref"].rsplit("/", 1)[1]]
        return schema

    def response_schema(path, method):
        responses = actual["paths"][path][method]["responses"]
        successful = [v for status, v in responses.items() if status.startswith("2")]
        assert len(successful) == 1
        return resolve(successful[0]["content"]["application/json"]["schema"])

    snapshot = response_schema(prefix + "/interventions/{intervention_id}/checklist", "get")
    assert snapshot["type"] == "object"
    assert {"id", "intervention_id", "template_id", "template_name", "template_version",
            "created_at", "items"} <= snapshot["properties"].keys()
    snapshot_items = snapshot["properties"]["items"]
    assert snapshot_items["type"] == "array"
    snapshot_item = resolve(snapshot_items["items"])
    assert {"id", "category", "label", "position", "result", "comment",
            "completed_at"} <= snapshot_item["properties"].keys()
    assert not {"checked", "note", "intervention_id"} & snapshot_item["properties"].keys()
    patch = actual["paths"][prefix + "/checklist-items/{item_id}"]["patch"]
    patch_schema = resolve(patch["requestBody"]["content"]["application/json"]["schema"])
    assert set(patch_schema["properties"]) == {"result", "comment"}
    assert not patch_schema.get("required")
    for field in ("result", "comment"):
        assert {"type": "null"} in patch_schema["properties"][field]["anyOf"]
    result_string = next(v for v in patch_schema["properties"]["result"]["anyOf"] if v.get("type") == "string")
    assert result_string["maxLength"] == 100
    assert "enum" not in result_string
    template_list = response_schema(prefix + "/checklist-templates", "get")
    assert template_list["type"] == "array"
    template_schema = resolve(template_list["items"])
    assert {"id", "name", "intervention_type", "version", "active",
            "items"} <= template_schema["properties"].keys()
    changed = {"InterventionCreate", "ChecklistItemRef", "ChecklistItemUpdate"}
    removed = {"BatchItemUpdate", "BatchUpdateRequest", "BatchUpdateResponse"}
    assert not removed & schemas.keys()
    for name, schema in old_schemas.items():
        if name not in changed | removed:
            assert schemas[name] == schema, name
    # New schemas must belong to the checklist feature, not silently replace
    # unrelated contracts. Names are chosen by runtime, not by this projection.
    assert all("Checklist" in name or name == "TemplateItem"
               for name in set(schemas) - set(old_schemas))
    create = deepcopy(schemas["InterventionCreate"])
    template = create["properties"].pop("checklist_template_id")
    integer = next(v for v in template["anyOf"] if v.get("type") == "integer")
    assert integer["exclusiveMinimum"] == 0
    assert {"type": "null"} in template["anyOf"]
    assert "checklist_template_id" not in create.get("required", [])
    assert create == old_schemas["InterventionCreate"]
    item = schemas["ChecklistItemRef"]["properties"]
    assert set(item) == {"id", "intervention_checklist_id", "category", "label",
                         "position", "result", "comment", "completed_at"}
    for key in ("id", "category", "label", "position"):
        assert item[key] == old_schemas["ChecklistItemRef"]["properties"][key]
    for key in ("result", "comment", "completed_at"):
        assert {"type": "null"} in item[key]["anyOf"]
    # Compare every other OpenAPI field, including unrelated routes and metadata.
    projected = deepcopy(actual)
    projected["paths"] = {p: v for p, v in actual["paths"].items() if p not in allowed_paths}
    reference = deepcopy(historical)
    reference["paths"] = {p: v for p, v in historical["paths"].items() if p not in old_paths}
    projected["components"]["schemas"] = {
        n: s for n, s in schemas.items() if n in old_schemas and n not in changed | removed
    }
    reference["components"]["schemas"] = {
        n: s for n, s in old_schemas.items() if n not in changed | removed
    }
    assert projected == reference
