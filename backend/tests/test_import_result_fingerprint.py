"""Unknown historical outcomes preserve fingerprints; actual outcomes stale plans."""
from datetime import date

import pytest
from fastapi import HTTPException

from app.modules.customers.models import Client, Site
from app.modules.interventions.models.intervention import Intervention, InterventionStatus
from tests.test_import_service_v2 import environment, stage_clients


@pytest.mark.asyncio
async def test_outcomes_are_unknown_compatible_but_not_ignored_in_import_approval(environment):
    service, sessions = environment
    async with sessions() as db:
        owner = Client(full_name="Historical fingerprint", phone="0987654321", address="Paris")
        db.add(owner)
        await db.flush()
        site = Site(client_id=owner.id, name="History", address="Paris")
        db.add(site)
        await db.flush()
        historical = Intervention(site_id=site.id, title="Historical unknown issue",
                                  scheduled_date=date(2020, 1, 1), status=InterventionStatus.COMPLETED)
        db.add(historical)
        await db.commit()
        historical_id = historical.id
    async with sessions() as db:
        pools, _, unknown_fingerprint = await service._load(db)
        assert "result" not in pools["interventions"][0]
    approved = await stage_clients(service)
    async with sessions() as db:
        historical = await db.get(Intervention, historical_id)
        historical.result = "PART_NEEDED"
        await db.commit()
    async with sessions() as db:
        pools, _, actual_fingerprint = await service._load(db)
        assert pools["interventions"][0]["result"] == "PART_NEEDED"
        assert actual_fingerprint != unknown_fingerprint
    with pytest.raises(HTTPException) as error:
        await service.execute(approved["id"], approved["plan_token"])
    assert error.value.status_code == 409
    async with sessions() as db:
        historical = await db.get(Intervention, historical_id)
        historical.result = None
        await db.commit()
    async with sessions() as db:
        _, _, restored = await service._load(db)
        assert restored == unknown_fingerprint
