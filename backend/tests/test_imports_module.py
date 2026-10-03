"""R0 functional replay. No business ambiguity is resolved by this recipe."""
import asyncio
import base64
from datetime import date, datetime
from enum import Enum
from hashlib import sha256
import json
import lzma
import os
from pathlib import Path
import tempfile

import pytest
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.base import Base
from app.model_registry import load_models
from app.modules.imports.models import ImportBatch, ImportRecord, ImportReference, ImportError
from app.modules.imports.service import ImportService

ROOT = Path(__file__).resolve().parents[2]
PACK = ROOT / "backend/tests/fixtures/excel"
SNAPSHOT = Path(__file__).parent / "fixtures/imports_refactor/before.json"
BEFORE_SOURCE_COMMIT = "bb1fc14c4d8da80e9584eb1ed6de1f69cd96132e"
BEFORE_ARTIFACT_SHA256 = "6fea24321f71239649f57be88e0270c5e704cce12a23ff1722d3aad0431d6279"
BEFORE_CANONICAL_SHA256 = "f98dd88686d7efc6446187e5507a8c49be5fe3be66453acc014b1fcbec502db2"
RECIPE = [
    ("01_clients_sites_equipements.xlsx", [
        {"sheet": "Clients", "kind": "clients"},
        {"sheet": "Sites", "kind": "sites"},
        {"sheet": "Equipements", "kind": "equipment"},
    ]),
    ("02_interventions_2018_2025.xlsx", [{"kind": "interventions"}]),
    ("03_export_ancien_format.xlsx", [{"kind": "interventions", "two_digit_year_base": 2000}]),
    ("04_export_clients_latin1.csv", [{"kind": "clients", "encoding": "latin-1", "separator": ";"}]),
]
# Only technical instants are normalized. Business dates and plan/fingerprint
# hashes, IDs, FKs, messages and all JSON values are kept verbatim.
INSTANTS = {"created_at", "updated_at", "completed_at", "lease_until"}


def normalized_column(table_name, key, v):
    # Completion of an Intervention/Installation is a business date. Only the
    # import journal's completion/lease instants are volatile execution metadata.
    technical_instant = key in {"created_at", "updated_at"} or (
        table_name == "import_batch" and key in {"completed_at", "lease_until"}
    )
    if technical_instant and v is not None:
        return "<instant>"
    if table_name == "import_batch" and key == "execution_token" and v is not None:
        return "<lease-token>"
    return value(v)


def value(v):
    if isinstance(v, bytes):
        # Exact bytes live in the hash-checked R0 pack, not duplicated as hex.
        return {"size": len(v), "sha256": sha256(v).hexdigest()}
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    if isinstance(v, Enum):
        return v.value
    return v


async def replay():
    baseline = json.loads((ROOT / "notes/backend/extras/refactor-monolithe-modulaire/R0-baseline.json").read_text())
    hashes = {}
    for name, expected in baseline["import_fixture_sha256"].items():
        actual = sha256((ROOT / name).read_bytes()).hexdigest()
        assert actual == expected, name
        hashes[name] = actual
    # Empty database is the explicit initial state (including users/catalog).
    # This exercises automatic creation and unresolved business decisions.
    with tempfile.TemporaryDirectory(prefix="tervo-import-replay-") as directory:
        engine = create_async_engine(f"sqlite+aiosqlite:///{directory}/replay.db")

        @event.listens_for(engine.sync_engine, "connect")
        def foreign_keys(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")

        try:
            load_models()
            async with engine.begin() as connection:
                await connection.run_sync(Base.metadata.create_all)
            factory = async_sessionmaker(engine, expire_on_commit=False)
            async with factory() as db:
                service = ImportService(db)
                steps = []
                for filename, selections in RECIPE:
                    content = (PACK / filename).read_bytes()
                    preview = await service.stage(content, filename, "r0-pack", selections)
                    preview = await service.detail(preview["id"], page_size=1000)
                    initial = await service.validate(preview["id"])
                    decisions = {}
                    if filename.startswith("01"):
                        # A deterministic technical display name, copied from the
                        # actual address; no identity/replacement is confirmed.
                        for row in initial["items"]:
                            if row["kind"] == "sites" and row["normalized"].get("site_address"):
                                decisions[row["key"]] = {
                                    "action": "create",
                                    "corrections": {"site_name": row["normalized"]["site_address"]},
                                    "note": "Recette technique R0 : nom du site = adresse source, sans arbitrage métier",
                                }
                    if filename.startswith("02"):
                        for row in initial["items"]:
                            if row["original"].get("Resultat") == "RESOLVED":
                                decisions[row["key"]] = {
                                    "action": "create",
                                    "corrections": {
                                        "title": row["original"]["Description"],
                                        "status": "COMPLETED",
                                    },
                                    "note": "Recette historique R0 : titre = Description ; RESOLVED traduit en COMPLETED, aucune identité corrigée",
                                }
                    plan = await service.validate(preview["id"], decisions) if decisions else initial
                    result = await service.execute(plan["id"], plan["plan_token"], batch_size=3)
                    # Repeat the exact bytes/namespace and the approved execution.
                    before = await dump_database(db)
                    repeated = await service.stage(content, filename, "r0-pack", selections)
                    assert repeated["id"] == plan["id"]
                    rerun = await service.execute(plan["id"], plan["plan_token"], batch_size=3)
                    after = await dump_database(db)
                    # Partial executions can change their completion instant only.
                    assert before == after
                    assert result == rerun
                    steps.append(dict(preview=preview, initial_validation=initial,
                                      decisions=decisions, approved=plan, execution=result,
                                      errors=await service.errors(plan["id"], page_size=1000),
                                      same_hash_reexecution=rerun))
                database = await dump_database(db)
                assert [s["execution"]["status"] for s in steps] == [
                    "partial", "partial", "partial", "success",
                ]
                assert len(database["equipment"]) == 3
                assert database["installation"] == []
                assert len(database["intervention"]) == 4
                assert any(e["code"] == "ORPHAN" for e in database["import_error"])
                assert not any(e["code"] == "BATCH_ROLLBACK" for e in database["import_error"])
                return dict(fixture_sha256=hashes, recipe=RECIPE, initial_state="all tables empty",
                            normalization={"column_instants": sorted(INSTANTS),
                                           "non_null_execution_token": "<lease-token>"},
                            steps=steps, database=database)
        finally:
            await engine.dispose()


async def dump_database(db):
    """Every column, then the verified INT-106/105/104 projections."""
    from tests.contract_int109 import project_import_database

    result = {}
    for table in sorted(Base.metadata.tables.values(), key=lambda t: t.name):
        rows = (await db.execute(select(table).order_by(*table.primary_key.columns))).mappings().all()
        result[table.name] = [
            {key: normalized_column(table.name, key, v) for key, v in row.items()}
            for row in rows
        ]
    return project_import_database(result)


def test_snapshot_normalization_preserves_business_completion_dates():
    instant = datetime(2026, 9, 28, 12, 30)
    for table in ("intervention", "installation"):
        assert normalized_column(table, "completed_at", instant) == instant.isoformat()
        assert normalized_column(table, "started_at", instant) == instant.isoformat()
    assert normalized_column("intervention", "scheduled_date", instant.date()) == "2026-09-28"
    assert normalized_column("import_batch", "completed_at", instant) == "<instant>"
    assert normalized_column("import_batch", "lease_until", instant) == "<instant>"
    assert normalized_column("import_batch", "execution_token", "lease") == "<lease-token>"
    assert normalized_column("import_batch", "plan_token", "approved") == "approved"
    assert normalized_column("import_batch", "database_snapshot", "fingerprint") == "fingerprint"
    assert normalized_column("intervention", "completed_at", None) is None


@pytest.mark.asyncio
async def test_r0_import_pack_matches_before_snapshot():
    actual = await replay()
    # JSON round-trip makes tuple/list representation identical to the artifact.
    artifact_bytes = SNAPSHOT.read_bytes()
    assert sha256(artifact_bytes).hexdigest() == BEFORE_ARTIFACT_SHA256
    artifact = json.loads(artifact_bytes)
    assert artifact["source_commit"] == BEFORE_SOURCE_COMMIT
    assert artifact["canonical_sha256"] == BEFORE_CANONICAL_SHA256
    expected_bytes = lzma.decompress(base64.b64decode(artifact["lzma_base64"]))
    assert sha256(expected_bytes).hexdigest() == BEFORE_CANONICAL_SHA256
    assert json.loads(json.dumps(actual, ensure_ascii=False)) == json.loads(expected_bytes)


@pytest.mark.asyncio
async def test_historical_intervention_without_equipment_or_commercial_chain(monkeypatch):
    from inspect import unwrap
    from sqlalchemy import func
    from app.modules.customers.models import Client, Site
    from app.modules.interventions.models.intervention import Intervention
    from tests.test_import_service_v2 import environment

    monkeypatch.delenv("TERVO_IMPORT_TEST_DATABASE_URL", raising=False)
    fixture = unwrap(environment)()
    try:
        service, factory = await anext(fixture)
        async with factory() as db:
            client = Client(full_name="Historique R9", phone="0102030405", address="Paris")
            db.add(client)
            await db.flush()
            site = Site(client_id=client.id, name="Site historique", address="Paris")
            db.add(site)
            await db.commit()
            site_id = site.id
        preview = await service.stage(
            b"Identifiant;Titre;Date\nH1;Entretien sans appareil;2020-01-02\n",
            "historical.csv", "r9-null-equipment",
            [{"kind": "interventions", "mapping": {
                "intervention_source_id": "Identifiant",
                "title": "Titre",
                "scheduled_date": "Date",
            }}],
        )
        approved = await service.validate(preview["id"], {
            preview["items"][0]["key"]: {
                "action": "create",
                "corrections": {"site_id": site_id, "status": "COMPLETED"},
                "note": "Recette fictive : site connu et statut approuvé, aucun équipement inventé",
            },
        })
        result = await service.execute(approved["id"], approved["plan_token"])
        assert result["status"] == "success" and result["counts"]["committed"] == 1
        async with factory() as db:
            intervention = await db.scalar(select(Intervention))
            assert intervention.site_id == site_id
            assert intervention.equipment_id is None
            assert intervention.scheduled_date == date(2020, 1, 2)
            assert intervention.completed_at is None
            record = await db.scalar(select(ImportRecord))
            assert record.entity_id == intervention.id and record.action == "create"
            for name in ("equipment", "installation", "sale", "sale_line"):
                assert await db.scalar(select(func.count()).select_from(Base.metadata.tables[name])) == 0
    finally:
        await fixture.aclose()


if __name__ == "__main__":
    # Capture is opt-in and writes only the caller's scratch destination.
    destination = Path(os.environ["TERVO_CAPTURE_SCRATCH"])
    destination.write_text(json.dumps(asyncio.run(replay()), ensure_ascii=False, indent=2) + "\n")
