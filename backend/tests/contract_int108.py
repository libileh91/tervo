"""Project only the INT-108 review delta before checking immutable R0–R11."""

from copy import deepcopy

from tests.contract_int107 import (
    assert_metadata_contract as previous_metadata,
    assert_openapi_contract as previous_openapi,
)

RATING_RULE = (
    "(submitted_at IS NULL AND rating IS NULL) OR "
    "(submitted_at IS NOT NULL AND rating BETWEEN 1 AND 5)"
)


def assert_metadata_contract(actual, historical):
    projected = deepcopy(actual)
    review = projected["review"]
    columns = {column["name"]: column for column in review["columns"]}
    assert columns["rating"] == {
        "name": "rating", "type": "INTEGER", "nullable": True,
        "primary_key": False, "server_default": None,
    }
    checks = [constraint for constraint in review["constraints"]
              if constraint["kind"] == "CheckConstraint"]
    assert checks == [{
        "kind": "CheckConstraint", "name": "ck_review_submission_rating",
        "columns": [], "definition": RATING_RULE, "foreign_keys": [],
    }]
    columns["rating"]["nullable"] = False
    review["constraints"].remove(checks[0])
    previous_metadata(projected, historical)


def assert_openapi_contract(actual, historical):
    projected = deepcopy(actual)
    operation = projected["paths"].pop("/api/v1/reviews")
    assert set(operation) == {"post"}
    post = operation["post"]
    assert not post.get("security")  # customer link, no JWT
    assert post["requestBody"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ReviewCreateRequest",
    }
    schema = projected["components"]["schemas"].pop("ReviewCreateRequest")
    assert set(schema["properties"]) == {
        "share_token", "rating", "comment", "reviewer_name",
    }
    assert set(schema["required"]) == {"share_token", "rating"}
    assert schema["properties"]["rating"]["minimum"] == 1
    assert schema["properties"]["rating"]["maximum"] == 5
    previous_openapi(projected, historical)
