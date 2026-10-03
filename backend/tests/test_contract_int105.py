"""Pure composition guards, without importing runtime or rewriting evidence."""

from copy import deepcopy

import pytest

from tests.contract_int104 import assert_metadata_contract as assert_metadata_contract104
from tests.contract_int105 import (
    PHOTO_BODY, USAGES, assert_metadata_contract, assert_openapi_contract,
    project_import_database,
)
from tests.test_contract_int104 import (
    current_metadata_example, current_openapi_example, historical_import_example,
)


def current_metadata105():
    current, historical = current_metadata_example()
    assert_metadata_contract104(current, historical)
    for new, old in (("photo", "intervention_photo"), ("material_usage", "material")):
        table = current.pop(old)
        current[new] = table
        for column in table["columns"]:
            if column["name"] == "category":
                column["name"] = "usage"
            elif column["name"] == "name":
                column["name"] = "designation"
            elif column["name"] == "quantity":
                column["type"] = "NUMERIC(12, 3)"
        if new == "material_usage":
            table["columns"].append({
                "name": "unit", "type": "VARCHAR(50)", "nullable": True,
                "primary_key": False, "server_default": None,
            })
        table["constraints"].append({
            "kind": "CheckConstraint", "columns": [], "foreign_keys": [],
            "name": "ck_photo_usage" if new == "photo" else "ck_material_usage_quantity_positive",
            "definition": (
                "usage IN ('BEFORE', 'AFTER', 'EQUIPMENT', 'ANOMALY', 'PART', 'OTHER')"
                if new == "photo" else "quantity > 0"
            ),
        })
    return current, historical


def test_metadata_composition_preserves_both_inputs():
    current, historical = current_metadata105()
    before = deepcopy((current, historical))
    assert_metadata_contract(current, historical)
    assert (current, historical) == before


@pytest.mark.parametrize("mutation", [
    "nullable", "extra-column", "wrong-fk", "enum", "quantity-type",
    "unrelated-column", "extra-table", "default",
])
def test_metadata_composition_rejects_undeclared_delta(mutation):
    current, historical = current_metadata105()
    if mutation == "nullable":
        current["photo"]["columns"][1]["nullable"] = True
    elif mutation == "extra-column":
        current["photo"]["columns"].append(deepcopy(current["material_usage"]["columns"][-1]))
    elif mutation == "wrong-fk":
        fk = next(c for c in current["photo"]["constraints"] if c["foreign_keys"])
        fk["foreign_keys"][0]["ondelete"] = "RESTRICT"
    elif mutation == "enum":
        current["photo"]["constraints"][-1]["definition"] += " OR usage = 'LEGACY'"
    elif mutation == "quantity-type":
        next(c for c in current["material_usage"]["columns"] if c["name"] == "quantity")["type"] = "FLOAT"
    elif mutation == "unrelated-column":
        current["product"]["columns"][0]["nullable"] = True
    elif mutation == "extra-table":
        current["unrelated"] = {}
    else:
        current["photo"]["columns"][0]["server_default"] = "1"
    with pytest.raises(AssertionError):
        assert_metadata_contract(current, historical)


def test_import_projection_preserves_history_and_input():
    current, historical = historical_import_example()
    current.update(photo=[], material_usage=[])
    historical.update(intervention_photo=[], material=[])
    before = deepcopy(current)
    assert project_import_database(current) == historical
    assert current == before


@pytest.mark.parametrize("table", ["photo", "material_usage"])
def test_import_projection_never_discards_nonempty_feature_data(table):
    current, _ = historical_import_example()
    current.update(photo=[], material_usage=[])
    current[table] = [{"id": 7}]
    with pytest.raises(AssertionError, match=table):
        project_import_database(current)


def current_openapi105():
    current, historical = current_openapi_example()
    schemas = current["components"]["schemas"]
    schemas["PhotoUsage"] = {"type": "string", "enum": sorted(USAGES)}
    usage = {"$ref": "#/components/schemas/PhotoUsage"}
    body = schemas[PHOTO_BODY]
    body["properties"]["usage"] = deepcopy(usage)
    body["properties"].pop("category")
    body["required"] = ["file", "usage"]
    photo = schemas["PhotoRef"]
    photo["properties"]["usage"] = deepcopy(usage)
    photo["properties"].pop("category")
    photo["required"] = ["id", "usage", "file_url"]
    create = schemas["MaterialCreate"]
    create["properties"] = {
        "designation": {"type": "string", "minLength": 1, "maxLength": 255},
        "unit": {"type": "string", "minLength": 1, "maxLength": 50},
        "quantity": {"anyOf": [
            {"type": "number", "exclusiveMinimum": 0},
            {"type": "string", "pattern": r"^\d{1,9}(?:\.\d{1,3})?$"},
        ]},
    }
    create["required"] = ["designation", "quantity", "unit"]
    create["additionalProperties"] = False
    response = schemas["MaterialResponse"]["properties"]
    response["designation"] = response.pop("name")
    response["quantity"] = {"anyOf": [{"type": "number"}, {"type": "null"}]}
    response["unit"] = {"anyOf": [{"type": "string"}, {"type": "null"}]}
    schemas["MaterialUpdate"] = {
        "properties": deepcopy(create["properties"]), "additionalProperties": False,
    }
    current["paths"]["/api/v1/interventions/{intervention_id}/photos"]["get"] = {
        "responses": {"200": {"content": {"application/json": {"schema": {
            "type": "array", "items": {"$ref": "#/components/schemas/PhotoRef"},
        }}}}},
    }
    return current, historical


def test_openapi_composition_preserves_inputs():
    current, historical = current_openapi105()
    before = deepcopy((current, historical))
    assert_openapi_contract(current, historical)
    assert (current, historical) == before


@pytest.mark.parametrize("mutation", [
    "enum", "category-alias", "required-quantity", "unbounded-quantity",
    "string-response", "extra-schema", "unrelated-route", "unrelated-schema",
])
def test_openapi_composition_rejects_undeclared_delta(mutation):
    current, historical = current_openapi105()
    schemas = current["components"]["schemas"]
    if mutation == "enum":
        schemas["PhotoUsage"]["enum"].append("LEGACY")
    elif mutation == "category-alias":
        schemas[PHOTO_BODY]["properties"]["category"] = {"type": "string"}
    elif mutation == "required-quantity":
        schemas["MaterialCreate"]["required"].remove("quantity")
    elif mutation == "unbounded-quantity":
        schemas["MaterialCreate"]["properties"]["quantity"]["anyOf"][1]["pattern"] = r"^\d+$"
    elif mutation == "string-response":
        schemas["MaterialResponse"]["properties"]["quantity"]["anyOf"][0]["type"] = "string"
    elif mutation == "extra-schema":
        schemas["UnexpectedPhotoFeature"] = {"type": "object"}
    elif mutation == "unrelated-route":
        current["paths"]["/undeclared"] = {}
    else:
        schemas["ProductCreate"]["properties"]["name"]["type"] = "integer"
    with pytest.raises(AssertionError):
        assert_openapi_contract(current, historical)
