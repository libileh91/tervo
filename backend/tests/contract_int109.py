"""Check the showroom delta before projecting onto the immutable R0–R11 guards."""

from copy import deepcopy

from tests.contract_int108 import assert_metadata_contract as previous_metadata
from tests.contract_int108 import assert_openapi_contract as previous_openapi
from tests.contract_int107 import project_import_database as previous_import


def assert_metadata_contract(actual, historical):
    projected = deepcopy(actual)
    visit = projected.pop("showroom_visit")
    links = projected.pop("showroom_visit_product")
    fields = {column["name"]: column for column in visit["columns"]}
    assert set(fields) == {
        "id", "client_id", "visitor_name", "visited_at", "salesperson_id",
        "follow_up_status", "notes", "created_at",
    }
    assert fields["id"]["primary_key"] and fields["id"]["type"] == "INTEGER"
    assert fields["client_id"]["nullable"] and fields["client_id"]["type"] == "INTEGER"
    assert not fields["salesperson_id"]["nullable"]
    assert not fields["visited_at"]["nullable"]
    assert fields["follow_up_status"]["type"] == "VARCHAR(30)"
    checks = {c["name"]: c["definition"] for c in visit["constraints"]
              if c["kind"] == "CheckConstraint"}
    assert checks == {
        "ck_showroom_visit_identity":
            "client_id IS NOT NULL OR (visitor_name IS NOT NULL AND length(trim(visitor_name)) > 0)",
        "ck_showroom_visit_follow_up_status":
            "follow_up_status IN ('TO_FOLLOW_UP', 'CONSIDERING', 'QUOTE_REQUESTED', 'QUOTE_SENT', 'SOLD', 'LOST', 'NO_FURTHER_ACTION')",
    }
    fk = {(tuple(c["columns"]), f["target"], f["ondelete"])
          for c in visit["constraints"] for f in c["foreign_keys"]}
    assert fk == {
        (("client_id",), "client.id", "RESTRICT"),
        (("salesperson_id",), "user.id", "RESTRICT"),
    }
    assert [(c["name"], c["primary_key"]) for c in links["columns"]] == [
        ("visit_id", True), ("product_id", True),
    ]
    fk = {(tuple(c["columns"]), f["target"], f["ondelete"])
          for c in links["constraints"] for f in c["foreign_keys"]}
    assert fk == {
        (("visit_id",), "showroom_visit.id", "CASCADE"),
        (("product_id",), "product.id", "RESTRICT"),
    }
    previous_metadata(projected, historical)


def assert_openapi_contract(actual, historical):
    projected = deepcopy(actual)
    paths = {
        "/api/v1/showroom/visits": {"get", "post"},
        "/api/v1/showroom/visits/{visit_id}": {"get", "patch"},
        "/api/v1/showroom/visits/{visit_id}/products": {"post"},
        "/api/v1/showroom/visits/{visit_id}/products/{product_id}": {"delete"},
    }
    for path, methods in paths.items():
        operations = projected["paths"].pop(path)
        assert set(operations) == methods
        assert all(operation.get("security") for operation in operations.values())
    schemas = projected["components"]["schemas"]
    create = schemas.pop("VisitCreate")
    assert set(create["properties"]) == {
        "client_id", "visitor_name", "visited_at", "salesperson_id",
        "follow_up_status", "notes",
    }
    assert create["required"] == ["visited_at"]
    response = schemas.pop("VisitResponse")
    assert set(response["properties"]) == {
        "id", "client_id", "visitor_name", "visited_at", "salesperson_id",
        "follow_up_status", "notes", "created_at", "product_ids",
    }
    update = schemas.pop("VisitUpdate")
    assert set(update["properties"]) == {
        "client_id", "visitor_name", "visited_at", "follow_up_status", "notes",
    }
    for name in ("VisitListResponse", "PresentedProductCreate", "FollowUpStatus"):
        schemas.pop(name)
    previous_openapi(projected, historical)


def project_import_database(database):
    projected = deepcopy(database)
    for name in ("showroom_visit", "showroom_visit_product"):
        assert projected.pop(name) == [], f"Import unexpectedly created {name}"
    return previous_import(projected)
