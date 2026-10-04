"""Validate the replacement request delta without changing frozen API baselines."""

from copy import deepcopy

from tests.contract_int109 import assert_metadata_contract, project_import_database
from tests.contract_int109 import assert_openapi_contract as previous_openapi


def assert_openapi_contract(actual, historical):
    projected = deepcopy(actual)
    schema = projected["components"]["schemas"]["EquipmentReplace"]
    assert set(schema["properties"]) == {
        "new_product_id", "installation_date", "serial_number",
        "commissioned_at", "warranty_start", "warranty_end", "notes",
    }
    assert not schema.get("required")
    for name in ("commissioned_at", "warranty_start", "warranty_end"):
        field = schema["properties"].pop(name)
        assert field["anyOf"] == [
            {"format": "date", "type": "string"}, {"type": "null"},
        ]
        assert field["title"] == " ".join(part.title() for part in name.split("_"))
    previous_openapi(projected, historical)
