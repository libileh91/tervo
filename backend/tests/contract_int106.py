"""Strict INT-106 delta, composed with the frozen INT-105/104/R0 guards."""

from copy import deepcopy

from tests.contract_int105 import (
    assert_metadata_contract as assert_metadata_contract105,
    assert_openapi_contract as assert_openapi_contract105,
    project_import_database as project_import_database105,
)

RESULTS = [
    "RESOLVED", "PARTIALLY_RESOLVED", "UNRESOLVED", "PART_NEEDED",
    "QUOTE_NEEDED", "RESCHEDULE",
]
FEATURE_SCHEMAS = (
    "InterventionResponse", "InterventionHistoryItem",
    "InterventionCompleteRequest", "InterventionCompleteResponse",
)
RESULT_COLUMN = {
    "name": "result", "type": "VARCHAR(30)", "nullable": True,
    "primary_key": False, "server_default": None,
}
RESULT_CHECK = {
    "kind": "CheckConstraint", "name": "ck_intervention_result",
    "columns": [], "foreign_keys": [],
    "definition": "result IN ('RESOLVED', 'PARTIALLY_RESOLVED', 'UNRESOLVED', 'PART_NEEDED', 'QUOTE_NEEDED', 'RESCHEDULE')",
}
RESULT_REF = {"$ref": "#/components/schemas/InterventionResult"}


def assert_metadata_contract(actual, historical):
    projected = deepcopy(actual)
    table = projected["intervention"]
    columns = [c for c in table["columns"] if c["name"] == "result"]
    assert columns == [RESULT_COLUMN]
    checks = [c for c in table["constraints"] if c["kind"] == "CheckConstraint"]
    assert checks == [RESULT_CHECK]
    table["columns"].remove(RESULT_COLUMN)
    table["constraints"].remove(RESULT_CHECK)
    assert_metadata_contract105(projected, historical)


def assert_openapi_contract(actual, historical):
    projected = deepcopy(actual)
    schemas = projected["components"]["schemas"]
    enum = schemas.pop("InterventionResult")
    assert enum == {
        "type": "string", "enum": RESULTS, "title": "InterventionResult",
    }
    for name in FEATURE_SCHEMAS:
        schema = schemas[name]
        field = schema["properties"].pop("result")
        required = schema.get("required", [])
        if name in {"InterventionResponse", "InterventionHistoryItem"}:
            # FastAPI may omit an explicit null default from the published schema.
            # Unknown remains nullable/optional; a business default is forbidden.
            assert field.pop("default", None) is None
            assert field == {"anyOf": [RESULT_REF, {"type": "null"}]}
            assert "result" not in required
        else:
            assert field == RESULT_REF
            assert required.count("result") == 1
            required.remove("result")
            if not required:
                schema.pop("required")
        if name == "InterventionCompleteRequest":
            assert schema.pop("additionalProperties") is False
    assert_openapi_contract105(projected, historical)


def project_import_database(database):
    projected = deepcopy(database)
    for row in projected["intervention"]:
        assert "result" in row and row["result"] is None, (
            "Historical intervention result must remain NULL", row
        )
        del row["result"]
    return project_import_database105(projected)
