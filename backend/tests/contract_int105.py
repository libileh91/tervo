"""Composed INT-105 projection; INT-104 and R0 evidence remain untouched."""

from copy import deepcopy
import re

from tests.contract_int104 import (
    assert_metadata_contract as assert_metadata_contract104,
    assert_openapi_contract as assert_openapi_contract104,
    project_import_database as project_import_database104,
)

RENAMED_TABLES = {"photo": "intervention_photo", "material_usage": "material"}
USAGES = {"BEFORE", "AFTER", "EQUIPMENT", "ANOMALY", "PART", "OTHER"}
PHOTO_BODY = "Body_upload_photo_api_v1_interventions__intervention_id__photos_post"
FEATURE_SCHEMAS = {
    PHOTO_BODY, "PhotoRef", "PhotoUsage",
    "MaterialCreate", "MaterialUpdate", "MaterialResponse",
}


def assert_metadata_contract(actual, historical):
    projected = deepcopy(actual)
    for new, old in RENAMED_TABLES.items():
        assert old not in actual
        table = actual[new]
        expected = deepcopy(historical[old])
        columns = expected["columns"]
        for column in columns:
            if column["name"] == "category":
                column["name"] = "usage"
            elif column["name"] == "name":
                column["name"] = "designation"
            elif column["name"] == "quantity":
                column["type"] = "NUMERIC(12, 3)"
        if new == "material_usage":
            columns.append({
                "name": "unit", "type": "VARCHAR(50)", "nullable": True,
                "primary_key": False, "server_default": None,
            })
        # Column ordering is not a business delta; every serialized attribute is.
        assert len(table["columns"]) == len(columns), new
        assert {c["name"]: c for c in table["columns"]} == {
            c["name"]: c for c in columns
        }, new
        checks = [c for c in table["constraints"] if c["kind"] == "CheckConstraint"]
        assert len(checks) == 1, new
        check = checks[0]
        assert check["columns"] == [] and check["foreign_keys"] == []
        if new == "photo":
            assert check["name"] == "ck_photo_usage"
            assert check["definition"] == (
                "usage IN ('BEFORE', 'AFTER', 'EQUIPMENT', 'ANOMALY', 'PART', 'OTHER')"
            )
        else:
            assert check["name"] == "ck_material_usage_quantity_positive"
            assert check["definition"] == "quantity > 0"
        assert sorted(
            (c for c in table["constraints"] if c["kind"] != "CheckConstraint"),
            key=repr,
        ) == sorted(expected["constraints"], key=repr), new
        assert set(table) == set(expected), new
        projected.pop(new)
        projected[old] = deepcopy(historical[old])
    assert_metadata_contract104(projected, historical)


def project_import_database(database):
    projected = deepcopy(database)
    for new, old in RENAMED_TABLES.items():
        assert old not in database
        assert database[new] == [], f"Import unexpectedly populated {new}"
        projected[old] = projected.pop(new)
    return project_import_database104(projected)


def assert_openapi_contract(actual, historical):
    projected = deepcopy(actual)
    schemas = actual["components"]["schemas"]

    def resolve(schema):
        return schemas[schema["$ref"].rsplit("/", 1)[1]] if "$ref" in schema else schema

    def enum(schema):
        schema = resolve(schema)
        assert schema["type"] == "string"
        assert set(schema["enum"]) == USAGES and len(schema["enum"]) == 6

    body = schemas[PHOTO_BODY]
    assert set(body["properties"]) == {"file", "usage"}
    assert set(body["required"]) == {"file", "usage"}
    assert body["properties"]["file"] == historical["components"]["schemas"][PHOTO_BODY]["properties"]["file"]
    enum(body["properties"]["usage"])
    photo = schemas["PhotoRef"]["properties"]
    assert set(photo) == {"id", "usage", "file_url", "thumbnail_url", "taken_at"}
    enum(photo["usage"])
    for field in set(photo) - {"usage"}:
        assert photo[field] == historical["components"]["schemas"]["PhotoRef"]["properties"][field]
    assert set(schemas["PhotoRef"]["required"]) == {"id", "usage", "file_url"}
    create = schemas["MaterialCreate"]
    assert set(create["properties"]) == {"designation", "quantity", "unit"}
    assert set(create["required"]) == {"designation", "quantity", "unit"}
    assert create["additionalProperties"] is False
    for name, limit in (("designation", 255), ("unit", 50)):
        field = create["properties"][name]
        assert field["type"] == "string"
        assert field["minLength"] == 1 and field["maxLength"] == limit
    quantity = create["properties"]["quantity"]
    variants = quantity.get("anyOf", [quantity])
    numeric = next(v for v in variants if v.get("type") == "number")
    assert numeric["exclusiveMinimum"] == 0
    assert not any(v.get("type") == "null" for v in variants)
    # Pydantic publishes Decimal precision on the string alternative, not the
    # JSON-number alternative. Test its language rather than freeze regex text.
    decimal = next(v for v in variants if v.get("type") == "string")
    pattern = decimal["pattern"]
    assert all(re.search(pattern, value) for value in ("1", "0.001", "999999999.999"))
    assert all(not re.search(pattern, value) for value in ("1000000000", "1.0001"))
    response = schemas["MaterialResponse"]["properties"]
    assert set(response) == {"id", "intervention_id", "designation", "quantity", "unit", "position"}
    assert {v["type"] for v in response["quantity"]["anyOf"]} == {"number", "null"}
    assert {v["type"] for v in response["unit"]["anyOf"]} == {"string", "null"}
    update = schemas["MaterialUpdate"]
    assert set(update["properties"]) == {"designation", "quantity", "unit"}
    assert not update.get("required")
    assert update["additionalProperties"] is False
    old_schemas = historical["components"]["schemas"]
    # Checklist additions remain governed by 104; all other additions are explicit.
    added = set(schemas) - set(old_schemas)
    assert all(n in FEATURE_SCHEMAS or "Checklist" in n or n == "TemplateItem" for n in added)
    for name in FEATURE_SCHEMAS:
        if name in old_schemas:
            projected["components"]["schemas"][name] = deepcopy(old_schemas[name])
        else:
            projected["components"]["schemas"].pop(name, None)
    feature_paths = {p for p in historical["paths"] if "/photos" in p or "/materials" in p}
    assert feature_paths <= actual["paths"].keys()
    photos = "/api/v1/interventions/{intervention_id}/photos"
    for path in feature_paths:
        expected_methods = set(historical["paths"][path]) | ({"get"} if path == photos else set())
        assert set(actual["paths"][path]) == expected_methods, path
        for operation in actual["paths"][path].values():
            assert operation["responses"]
        projected["paths"][path] = deepcopy(historical["paths"][path])
    get = actual["paths"][photos]["get"]
    listing = resolve(get["responses"]["200"]["content"]["application/json"]["schema"])
    assert listing["type"] == "array"
    assert resolve(listing["items"]) == schemas["PhotoRef"]
    assert_openapi_contract104(projected, historical)
