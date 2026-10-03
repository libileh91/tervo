"""INT-104 on disposable legacy schemas; no application database or fixtures."""
import importlib.util
import os
from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy.exc import IntegrityError


_LEGACY_SELECT = "SELECT id, intervention_id, category, label, checked, note, position FROM checklist_item ORDER BY id"


@pytest.fixture
def migrated():
    path = Path(__file__).parents[1] / "alembic/versions/g104e0010001_checklist_snapshots.py"
    spec = importlib.util.spec_from_file_location("checklist_revision", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    engine = sa.create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        connection.exec_driver_sql("CREATE TABLE intervention (id INTEGER PRIMARY KEY)")
        connection.exec_driver_sql(
            "CREATE TABLE checklist_item (id INTEGER PRIMARY KEY, intervention_id INTEGER NOT NULL "
            "REFERENCES intervention(id) ON DELETE CASCADE, category VARCHAR(20) NOT NULL, "
            "label VARCHAR(255) NOT NULL, checked BOOLEAN NOT NULL, note TEXT, position INTEGER NOT NULL)"
        )
        connection.exec_driver_sql("CREATE INDEX ix_checklist_item_id ON checklist_item(id)")
        connection.exec_driver_sql("CREATE INDEX ix_checklist_item_intervention_id ON checklist_item(intervention_id)")
        connection.exec_driver_sql("INSERT INTO intervention VALUES (1), (2)")
        connection.exec_driver_sql(
            "INSERT INTO checklist_item VALUES "
            "(7, 1, 'safety', 'Contrôle été', 1, 'Commentaire conservé', 3), "
            "(19, 1, 'other', 'Second', 0, NULL, 9)"
        )
        before = connection.exec_driver_sql(_LEGACY_SELECT).all()
        module.op = Operations(MigrationContext.configure(connection))
        module.upgrade()
        yield connection, module, before
    engine.dispose()


def test_historical_snapshots_and_lossless_roundtrip(migrated):
    connection, revision, before = migrated
    assert connection.exec_driver_sql(
        "SELECT intervention_id, template_id, template_name, template_version "
        "FROM intervention_checklist ORDER BY intervention_id"
    ).all() == [(1, None, "Checklist historique", 1), (2, None, "Checklist historique", 1)]
    assert connection.exec_driver_sql(
        "SELECT id, category, label, result, comment, position, completed_at FROM checklist_item ORDER BY id"
    ).all() == [
        (7, "safety", "Contrôle été", "OK", "Commentaire conservé", 3, None),
        (19, "other", "Second", None, None, 9, None),
    ]
    indexes = sa.inspect(connection).get_indexes("checklist_item")
    assert {index["name"] for index in indexes} == {
        "ix_checklist_item_id", "ix_checklist_item_intervention_checklist_id"
    }
    inspector = sa.inspect(connection)
    assert inspector.get_indexes("checklist_template") == []
    assert inspector.get_indexes("intervention_checklist") == []
    assert inspector.get_unique_constraints("intervention_checklist")[0]["column_names"] == ["intervention_id"]
    assert connection.exec_driver_sql(
        "SELECT count(*) FROM intervention_checklist WHERE created_at IS NULL"
    ).scalar_one() == 0
    assert connection.exec_driver_sql(
        "SELECT count(*) FROM checklist_template"
    ).scalar_one() == 0
    revision.downgrade()
    assert connection.exec_driver_sql(_LEGACY_SELECT).all() == before
    revision.upgrade()
    revision.downgrade()
    assert connection.exec_driver_sql(_LEGACY_SELECT).all() == before


@pytest.mark.parametrize("statement,reason", [
    ("INSERT INTO checklist_template VALUES (1, 'Modèle', 'maintenance', 1, 1, '[]')", "templates"),
    ("UPDATE intervention_checklist SET template_name='Métier' WHERE intervention_id=1", "provenance"),
    ("UPDATE intervention_checklist SET template_version=2 WHERE intervention_id=1", "provenance"),
    ("UPDATE checklist_item SET result='KO' WHERE id=7", "results"),
    ("UPDATE checklist_item SET completed_at=CURRENT_TIMESTAMP WHERE id=7", "timestamps"),
])
def test_downgrade_rejects_information_loss_before_ddl(migrated, statement, reason):
    connection, revision, _ = migrated
    connection.exec_driver_sql(statement)
    before = connection.exec_driver_sql("SELECT * FROM checklist_item ORDER BY id").all()
    with pytest.raises(RuntimeError, match=reason):
        revision.downgrade()
    assert connection.exec_driver_sql("SELECT * FROM checklist_item ORDER BY id").all() == before
    assert "intervention_checklist" in sa.inspect(connection).get_table_names()


@pytest.mark.parametrize("statement", [
    "UPDATE intervention_checklist SET template_version=0",
    "INSERT INTO intervention_checklist (intervention_id, template_name, template_version) VALUES (1, 'x', 1)",
    "UPDATE checklist_item SET intervention_checklist_id=999",
    "UPDATE checklist_item SET intervention_checklist_id=NULL",
    "INSERT INTO checklist_template VALUES (1, 'x', 'maintenance', 0, 1, '[]')",
])
def test_constraints(migrated, statement):
    connection, _, _ = migrated
    with pytest.raises(IntegrityError):
        connection.exec_driver_sql(statement)


def test_cascade_deletes_snapshot_and_items(migrated):
    connection, _, _ = migrated
    connection.exec_driver_sql("DELETE FROM intervention WHERE id=1")
    assert connection.exec_driver_sql("SELECT count(*) FROM checklist_item").scalar_one() == 0
    assert connection.exec_driver_sql("SELECT intervention_id FROM intervention_checklist").all() == [(2,)]


def test_template_reference_is_restricted(migrated):
    connection, _, _ = migrated
    connection.exec_driver_sql("INSERT INTO checklist_template VALUES (1, 'x', 'maintenance', 1, 1, '[]')")
    connection.exec_driver_sql("UPDATE intervention_checklist SET template_id=1 WHERE intervention_id=1")
    with pytest.raises(IntegrityError):
        connection.exec_driver_sql("DELETE FROM checklist_template WHERE id=1")


def test_postgresql_real_chain_roundtrip():
    """Opt-in: point only at a disposable PostgreSQL instance, never production.

    Run the real revisions without env.py, so application DATABASE_URL and model
    imports cannot accidentally redirect this test toward an existing database.
    All DDL is confined to a unique schema and rolled back, including enum types.
    """
    url = os.environ.get("TERVO_CHECKLIST_MIGRATION_TEST_URL")
    if not url:
        pytest.skip("TERVO_CHECKLIST_MIGRATION_TEST_URL not set (disposable PostgreSQL only)")
    engine = sa.create_engine(url)
    assert engine.dialect.name == "postgresql"
    config = Config()
    config.set_main_option("script_location", str(Path(__file__).parents[1] / "alembic"))
    scripts = ScriptDirectory.from_config(config)
    revisions = list(scripts.walk_revisions(base="base", head="g104e0010001"))
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            schema = f"checklist_test_{uuid4().hex}"
            connection.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
            connection.exec_driver_sql(f'SET LOCAL search_path TO "{schema}"')
            context = MigrationContext.configure(connection)
            with Operations.context(context):
                for revision in reversed(revisions):
                    revision.module.upgrade()
                assert "intervention_checklist" in sa.inspect(connection).get_table_names()
                revisions[0].module.downgrade()
                assert "intervention_checklist" not in sa.inspect(connection).get_table_names()
                revisions[0].module.upgrade()
                for revision in revisions:
                    revision.module.downgrade()
                assert sa.inspect(connection).get_table_names() == []
        finally:
            transaction.rollback()
    engine.dispose()
