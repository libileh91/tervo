"""Pure strict-delta tests: no runtime imports and no mutable R0 evidence."""

from copy import deepcopy

import pytest

from tests.contract_int106 import (
    FEATURE_SCHEMAS, RESULTS, RESULT_CHECK, RESULT_COLUMN, RESULT_REF,
    assert_metadata_contract, assert_openapi_contract, project_import_database,
)
from tests.test_contract_int105 import current_metadata105, current_openapi105
from tests.test_contract_int104 import historical_import_example


def current_metadata106():
    current, historical = current_metadata105()
    current["intervention"]["columns"].append(deepcopy(RESULT_COLUMN))
    current["intervention"]["constraints"].append(deepcopy(RESULT_CHECK))
    return current, historical


def current_openapi106():
    current, historical = current_openapi105()
    schemas = current["components"]["schemas"]
    schemas["InterventionResult"] = {
        "type": "string", "enum": list(RESULTS), "title": "InterventionResult",
    }
    for name in FEATURE_SCHEMAS:
        schema = schemas[name]
        if name in {"InterventionResponse", "InterventionHistoryItem"}:
            field = {"anyOf": [deepcopy(RESULT_REF), {"type": "null"}], "default": None}
        else:
            field = deepcopy(RESULT_REF)
            schema.setdefault("required", []).append("result")
        schema["properties"]["result"] = field
    schemas["InterventionCompleteRequest"]["additionalProperties"] = False
    return current, historical


@pytest.mark.parametrize("factory,guard", [
    (current_metadata106, assert_metadata_contract),
    (current_openapi106, assert_openapi_contract),
])
def test_composition_preserves_inputs(factory, guard):
    current, historical = factory()
    before = deepcopy((current, historical))
    guard(current, historical)
    assert (current, historical) == before


@pytest.mark.parametrize("mutation", [
    "nullable", "type", "default", "duplicate-column", "extra-column",
    "typo", "extra-check", "unrelated-column", "extra-table",
])
def test_metadata_rejects_undeclared_delta_without_mutation(mutation):
    current, historical = current_metadata106()
    table = current["intervention"]
    column = table["columns"][-1]
    if mutation == "nullable":
        column["nullable"] = False
    elif mutation == "type":
        column["type"] = "VARCHAR(31)"
    elif mutation == "default":
        column["server_default"] = "'RESOLVED'"
    elif mutation == "duplicate-column":
        table["columns"].append(deepcopy(column))
    elif mutation == "extra-column":
        table["columns"].append({**column, "name": "unexpected"})
    elif mutation == "typo":
        table["constraints"][-1]["definition"] += " OR result = 'RESOLVEDD'"
    elif mutation == "extra-check":
        table["constraints"].append(deepcopy(RESULT_CHECK))
    elif mutation == "unrelated-column":
        current["product"]["columns"][0]["nullable"] = True
    else:
        current["unexpected"] = {}
    before = deepcopy((current, historical))
    with pytest.raises(AssertionError):
        assert_metadata_contract(current, historical)
    assert (current, historical) == before


@pytest.mark.parametrize("mutation", [
    "extra-enum", "typo-enum", "required-missing", "nullable-request",
    "nullable-response", "resolved-default", "forbid", "observations",
    "generic-result", "unrelated-schema", "unrelated-route", "security",
    "closure-metadata",
])
def test_openapi_rejects_undeclared_delta_without_mutation(mutation):
    current, historical = current_openapi106()
    schemas = current["components"]["schemas"]
    request = schemas["InterventionCompleteRequest"]
    if mutation == "extra-enum":
        schemas["InterventionResult"]["enum"].append("LEGACY")
    elif mutation == "typo-enum":
        schemas["InterventionResult"]["enum"][0] = "RESOLVEDD"
    elif mutation == "required-missing":
        request["required"].remove("result")
    elif mutation == "nullable-request":
        request["properties"]["result"] = {"anyOf": [RESULT_REF, {"type": "null"}]}
    elif mutation == "nullable-response":
        schemas["InterventionHistoryItem"]["properties"]["result"]["anyOf"] = [RESULT_REF]
    elif mutation == "resolved-default":
        schemas["InterventionResponse"]["properties"]["result"]["default"] = "RESOLVED"
    elif mutation == "forbid":
        request["additionalProperties"] = True
    elif mutation == "observations":
        request["properties"]["observations"] = {"type": "integer"}
    elif mutation == "generic-result":
        schemas["InterventionCreate"]["properties"]["result"] = RESULT_REF
    elif mutation == "unrelated-schema":
        schemas["ProductCreate"]["properties"]["name"]["type"] = "integer"
    elif mutation == "unrelated-route":
        current["paths"]["/undeclared"] = {}
    elif mutation == "security":
        current["components"]["securitySchemes"] = {}
    else:
        current["paths"]["/api/v1/interventions/{intervention_id}/complete"]["put"]["summary"] = "Changed"
    before = deepcopy((current, historical))
    with pytest.raises(AssertionError):
        assert_openapi_contract(current, historical)
    assert (current, historical) == before


@pytest.mark.parametrize("result", [None, *RESULTS, "RESOLVEDD"])
def test_import_projection_requires_null_and_preserves_inputs(result):
    current, historical = historical_import_example()
    current.update(photo=[], material_usage=[])
    historical.update(intervention_photo=[], material=[])
    current["intervention"] = [{**row, "result": result} for row in current["intervention"]]
    before = deepcopy(current)
    if result is None:
        assert project_import_database(current) == historical
    else:
        with pytest.raises(AssertionError, match="NULL"):
            project_import_database(current)
    assert current == before


def test_import_projection_requires_result_column():
    current, _ = historical_import_example()
    current.update(photo=[], material_usage=[])
    before = deepcopy(current)
    with pytest.raises(AssertionError, match="NULL"):
        project_import_database(current)
    assert current == before
