"""Explicit archive delta composed with the immutable INT-106/R0 evidence."""
from copy import deepcopy
from tests.contract_int106 import (
    assert_metadata_contract as previous_metadata,
    assert_openapi_contract as previous_openapi,
    project_import_database as previous_import,
)


def assert_metadata_contract(actual, historical):
    projected = deepcopy(actual)
    fields = {
        "report": {"id", "intervention_id", "created_at"},
        "report_version": {"id", "report_id", "version", "request_key", "pdf", "sha256", "size",
                           "generated_at", "generated_by_id", "transmitted_at", "transmitted_by_id"},
    }
    for name, expected in fields.items():
        table = projected.pop(name)
        columns = {c["name"]: c for c in table["columns"]}
        assert set(columns) == expected
        assert columns["id"]["primary_key"]
        for key in expected - {"id"}:
            assert not columns[key]["primary_key"]
        nullable = {"request_key", "generated_by_id", "transmitted_at", "transmitted_by_id"}
        for key in expected:
            assert columns[key]["nullable"] == (key in nullable)
        fks = {(tuple(c["columns"]), f["target"], f["ondelete"])
               for c in table["constraints"] for f in c["foreign_keys"]}
        assert fks == (
            {(("intervention_id",), "intervention.id", "RESTRICT")} if name == "report" else
            {(("report_id",), "report.id", "RESTRICT"),
             (("generated_by_id",), "user.id", "SET NULL"),
             (("transmitted_by_id",), "user.id", "SET NULL")}
        )
        uniques = {tuple(c["columns"]) for c in table["constraints"] if c["kind"] == "UniqueConstraint"}
        assert uniques == ({("intervention_id",)} if name == "report" else
                           {("report_id", "version"), ("report_id", "request_key")})
        checks = {c["definition"] for c in table["constraints"] if c["kind"] == "CheckConstraint"}
        assert checks == (set() if name == "report" else {"version >= 1", "size > 0"})
        if name == "report_version":
            assert columns["pdf"]["type"] == "BYTEA"
            assert columns["sha256"]["type"] == "VARCHAR(64)"
            assert columns["request_key"]["type"] == "VARCHAR(100)"
    previous_metadata(projected, historical)


def assert_openapi_contract(actual, historical):
    projected = deepcopy(actual)
    new_paths = {
        "/api/v1/interventions/{intervention_id}/reports": {"get", "post"},
        "/api/v1/reports/{report_id}": {"get"},
        "/api/v1/reports/{report_id}/versions/{v}": {"get"},
        "/api/v1/reports/{report_id}/versions/{v}/transmit": {"post"},
    }
    for path, methods in new_paths.items():
        operations = projected["paths"].pop(path)
        assert set(operations) == methods
        assert all(operation["security"] for operation in operations.values())
    schemas = projected["components"]["schemas"]
    version = schemas.pop("ReportVersionResponse")
    assert set(version["properties"]) == {
        "id", "report_id", "version", "sha256", "size", "generated_at", "generated_by_id",
        "transmitted_at", "transmitted_by_id", "status", "storage_key",
    }
    assert "pdf" not in version["properties"]
    logical = schemas.pop("ReportResponse")
    assert set(logical["properties"]) == {"id", "intervention_id", "created_at", "versions"}
    confirmation = schemas.pop("TransmissionConfirmation")
    assert confirmation["additionalProperties"] is False
    assert confirmation["required"] == ["confirmed"]
    assert confirmation["properties"]["confirmed"]["type"] == "boolean"
    download = "/api/v1/interventions/{intervention_id}/report/download"
    assert set(actual["paths"][download]) == {"get"}
    for path in (download, "/api/v1/reports/{report_id}/versions/{v}"):
        assert "application/pdf" in actual["paths"][path]["get"]["responses"]["200"]["content"]
    projected["paths"][download] = deepcopy(historical["paths"][download])
    previous_openapi(projected, historical)


def project_import_database(database):
    projected = deepcopy(database)
    for name in ("report", "report_version"):
        assert projected.pop(name) == [], "Imports must not invent historical documents"
    return previous_import(projected)
