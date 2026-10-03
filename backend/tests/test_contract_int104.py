"""Pure guard tests: no runtime imports, SQL, fixture writes or R0 recapture."""

from copy import deepcopy
import json
from pathlib import Path

import pytest

from tests.contract_int104 import (
    assert_metadata_contract, assert_openapi_contract, project_import_database,
)

BASELINES = Path(__file__).resolve().parents[2] / "notes/backend/extras/refactor-monolithe-modulaire"


def historical_import_example():
    historical = {"checklist_item": [], "intervention": [{"id": 7, "title": "R0"}]}
    current = {**historical, "checklist_template": [], "intervention_checklist": [{
        "id": 1, "intervention_id": 7, "template_id": None,
        "template_name": "Checklist historique", "template_version": 1,
        "created_at": "2026-10-02T00:00:00",
    }]}
    return current, historical


def test_empty_checklist_projection_preserves_every_historical_row_and_column():
    current, historical = historical_import_example()
    original = deepcopy(current)
    assert project_import_database(current) == historical
    assert current == original


@pytest.mark.parametrize("table", ["checklist_item", "checklist_template"])
def test_import_projection_rejects_any_checklist_data(table):
    current, _ = historical_import_example()
    current[table] = [{"id": 1}]
    with pytest.raises(AssertionError, match=table):
        project_import_database(current)


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "unknown-intervention",
                                    "template", "name", "version", "timestamp"])
def test_import_projection_rejects_invented_or_missing_history(mutation):
    current, _ = historical_import_example()
    snapshot = current["intervention_checklist"][0]
    if mutation == "missing":
        current["intervention_checklist"] = []
    elif mutation == "duplicate":
        current["intervention_checklist"].append(deepcopy(snapshot))
    elif mutation == "unknown-intervention":
        snapshot["intervention_id"] = 99
    elif mutation == "template":
        snapshot["template_id"] = 1
    elif mutation == "name":
        snapshot["template_name"] = "Invented controls"
    elif mutation == "version":
        snapshot["template_version"] = 2
    else:
        snapshot["created_at"] = None
    with pytest.raises(AssertionError):
        project_import_database(current)


def test_import_projection_requires_both_new_tables():
    with pytest.raises(AssertionError):
        project_import_database({"checklist_item": []})


def test_r0_runtime_is_no_longer_a_valid_current_metadata_contract():
    historical = json.loads((BASELINES / "R0-metadata.json").read_text())
    with pytest.raises(AssertionError):
        assert_metadata_contract(historical, historical)


def current_metadata_example():
    historical = json.loads((BASELINES / "R0-metadata.json").read_text())
    current = deepcopy(historical)

    def constraint(kind, columns, target=None, ondelete=None):
        return {
            "kind": kind, "name": None, "columns": columns, "definition": None,
            "foreign_keys": [] if target is None else [{
                "target": target, "ondelete": ondelete, "onupdate": None,
            }],
        }

    def table(columns, fks=()):
        return {
            "columns": [{
                "name": name, "type": kind, "nullable": nullable,
                "primary_key": name == "id", "server_default": None,
            } for name, kind, nullable in columns],
            "constraints": [constraint("PrimaryKeyConstraint", ["id"])] + [
                constraint("ForeignKeyConstraint", [source], target, deletion)
                for source, target, deletion in fks
            ],
        }

    current["checklist_template"] = table([
        ("id", "INTEGER", False), ("name", "VARCHAR(255)", False),
        ("intervention_type", "VARCHAR(100)", False), ("version", "INTEGER", False),
        ("active", "BOOLEAN", False), ("items", "JSON", False),
    ])
    check = constraint("CheckConstraint", [])
    check.update(name="ck_checklist_template_version", definition="version >= 1")
    current["checklist_template"]["constraints"].append(check)
    current["intervention_checklist"] = table([
        ("id", "INTEGER", False), ("intervention_id", "INTEGER", False),
        ("template_id", "INTEGER", True), ("template_name", "VARCHAR(255)", False),
        ("template_version", "INTEGER", False),
        ("created_at", "TIMESTAMP WITHOUT TIME ZONE", False),
    ], [
        ("intervention_id", "intervention.id", "CASCADE"),
        ("template_id", "checklist_template.id", "RESTRICT"),
    ])
    constraints = current["intervention_checklist"]["constraints"]
    constraints.append(constraint("UniqueConstraint", ["intervention_id"]))
    check = constraint("CheckConstraint", [])
    check.update(name="ck_intervention_checklist_template_version", definition="template_version >= 1")
    constraints.append(check)
    current["checklist_item"] = table([
        ("id", "INTEGER", False), ("intervention_checklist_id", "INTEGER", False),
        ("category", "VARCHAR(20)", False), ("label", "VARCHAR(255)", False),
        ("position", "INTEGER", False), ("result", "VARCHAR(100)", True),
        ("comment", "TEXT", True), ("completed_at", "TIMESTAMP WITHOUT TIME ZONE", True),
    ], [("intervention_checklist_id", "intervention_checklist.id", "CASCADE")])
    return current, historical


def test_metadata_projection_accepts_explicit_delta_without_mutation():
    current, historical = current_metadata_example()
    before = deepcopy((current, historical))
    assert_metadata_contract(current, historical)
    assert (current, historical) == before


@pytest.mark.parametrize("mutation", ["extra-table", "unrelated-column", "old-column",
                                    "nullable-parent", "wrong-fk", "missing-unique"])
def test_metadata_projection_rejects_contract_drift(mutation):
    current, historical = current_metadata_example()
    if mutation == "extra-table":
        current["unexpected"] = {}
    elif mutation == "unrelated-column":
        current["product"]["columns"][0]["nullable"] = True
    elif mutation == "old-column":
        current["checklist_item"]["columns"].append(historical["checklist_item"]["columns"][1])
    elif mutation == "nullable-parent":
        current["checklist_item"]["columns"][1]["nullable"] = True
    elif mutation == "wrong-fk":
        current["checklist_item"]["constraints"][1]["foreign_keys"][0]["ondelete"] = "RESTRICT"
    else:
        current["intervention_checklist"]["constraints"] = [
            c for c in current["intervention_checklist"]["constraints"] if c["kind"] != "UniqueConstraint"
        ]
    with pytest.raises(AssertionError):
        assert_metadata_contract(current, historical)


def current_openapi_example():
    """Synthetic current contract, derived in memory; never rewrites evidence."""
    historical = json.loads((BASELINES / "R0-openapi.json").read_text())
    current = deepcopy(historical)
    current["paths"] = {p: v for p, v in current["paths"].items() if "/checklist" not in p}
    schemas = current["components"]["schemas"]
    for name in ("BatchItemUpdate", "BatchUpdateRequest", "BatchUpdateResponse"):
        schemas.pop(name)
    nullable_string = {"anyOf": [{"type": "string"}, {"type": "null"}]}
    schemas["InterventionCreate"]["properties"]["checklist_template_id"] = {
        "anyOf": [{"type": "integer", "exclusiveMinimum": 0}, {"type": "null"}],
    }
    item = schemas["ChecklistItemRef"]
    for key in ("checked", "note"):
        item["properties"].pop(key)
    item["required"].remove("checked")
    item["properties"]["intervention_checklist_id"] = {"type": "integer"}
    item["required"].append("intervention_checklist_id")
    for key in ("result", "comment", "completed_at"):
        item["properties"][key] = deepcopy(nullable_string)
    schemas["ChecklistItemUpdate"] = {
        "properties": {"result": deepcopy(nullable_string), "comment": deepcopy(nullable_string)},
    }
    schemas["ChecklistItemUpdate"]["properties"]["result"]["anyOf"][0]["maxLength"] = 100
    schemas["ChecklistSnapshot"] = {
        "type": "object",
        "properties": {
            **{key: {"type": "integer"} for key in (
                "id", "intervention_id", "template_id", "template_version",
            )},
            "template_name": {"type": "string"}, "created_at": {"type": "string"},
            "items": {"type": "array", "items": {"$ref": "#/components/schemas/ChecklistItemRef"}},
        },
    }
    schemas["ChecklistTemplate"] = {
        "type": "object",
        "properties": {key: {} for key in (
            "id", "name", "intervention_type", "version", "active", "items",
        )},
    }

    def operation(schema):
        return {"responses": {"200": {"content": {"application/json": {"schema": schema}}}}}

    prefix = "/api/v1"
    current["paths"][prefix + "/interventions/{intervention_id}/checklist"] = {
        "get": operation({"$ref": "#/components/schemas/ChecklistSnapshot"}),
    }
    current["paths"][prefix + "/checklist-templates"] = {
        "get": operation({"type": "array", "items": {"$ref": "#/components/schemas/ChecklistTemplate"}}),
        "post": operation({"$ref": "#/components/schemas/ChecklistTemplate"}),
    }
    current["paths"][prefix + "/checklist-templates/{template_id}"] = {
        "patch": operation({"$ref": "#/components/schemas/ChecklistTemplate"}),
    }
    patch = operation({"$ref": "#/components/schemas/ChecklistItemRef"})
    patch["requestBody"] = {"content": {"application/json": {
        "schema": {"$ref": "#/components/schemas/ChecklistItemUpdate"},
    }}}
    current["paths"][prefix + "/checklist-items/{item_id}"] = {"patch": patch}
    return current, historical


def test_openapi_projection_accepts_only_explicit_checklist_delta_without_mutation():
    current, historical = current_openapi_example()
    before = deepcopy((current, historical))
    assert_openapi_contract(current, historical)
    assert (current, historical) == before


@pytest.mark.parametrize("mutation", ["unrelated-schema", "unrelated-route", "old-method",
                                    "missing-snapshot-items", "old-item-field",
                                    "unbounded-result", "required-template"])
def test_openapi_projection_rejects_contract_drift(mutation):
    current, historical = current_openapi_example()
    schemas = current["components"]["schemas"]
    if mutation == "unrelated-schema":
        schemas["ProductCreate"]["properties"]["name"]["type"] = "integer"
    elif mutation == "unrelated-route":
        path = next(p for p in current["paths"] if "/checklist" not in p)
        current["paths"].pop(path)
    elif mutation == "old-method":
        current["paths"]["/api/v1/interventions/{intervention_id}/checklist"]["post"] = {}
    elif mutation == "missing-snapshot-items":
        schemas["ChecklistSnapshot"]["properties"].pop("items")
    elif mutation == "old-item-field":
        schemas["ChecklistItemRef"]["properties"]["checked"] = {"type": "boolean"}
    elif mutation == "unbounded-result":
        schemas["ChecklistItemUpdate"]["properties"]["result"]["anyOf"][0]["maxLength"] = 101
    else:
        schemas["InterventionCreate"]["required"].append("checklist_template_id")
    with pytest.raises(AssertionError):
        assert_openapi_contract(current, historical)
