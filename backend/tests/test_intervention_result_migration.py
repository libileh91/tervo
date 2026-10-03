"""INT-106 migration: disposable legacy SQLite and opt-in PostgreSQL schemas."""
import importlib.util
import os
from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory


@pytest.fixture
def legacy():
    path = Path(__file__).parents[1] / "alembic/versions/i106e0010001_intervention_result.py"
    spec = importlib.util.spec_from_file_location("result_revision", path)
    revision = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(revision)
    engine = sa.create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE intervention (id INTEGER PRIMARY KEY, status VARCHAR(20), "
            "observations TEXT, completed_at DATETIME)"
        )
        connection.exec_driver_sql(
            "INSERT INTO intervention VALUES "
            "(1, 'COMPLETED', 'Imported history', '2026-01-01'), "
            "(2, 'IN_PROGRESS', 'Existing notes', NULL)"
        )
        revision.op = Operations(MigrationContext.configure(connection))
        yield connection, revision
    engine.dispose()


def snapshot(connection):
    inspector = sa.inspect(connection)
    return (
        connection.exec_driver_sql("SELECT * FROM intervention ORDER BY id").all(),
        [(c["name"], str(c["type"]), c["nullable"], c["default"])
         for c in inspector.get_columns("intervention")],
        inspector.get_check_constraints("intervention"),
        inspector.get_indexes("intervention"),
    )


def test_historical_rows_unknown_and_roundtrip(legacy):
    connection, revision = legacy
    before = snapshot(connection)
    revision.upgrade()
    assert connection.exec_driver_sql("SELECT result FROM intervention").all() == [(None,), (None,)]
    column = next(c for c in sa.inspect(connection).get_columns("intervention") if c["name"] == "result")
    assert column["nullable"] is True
    assert str(column["type"]) == "VARCHAR(30)"
    assert column["default"] is None
    constraints = sa.inspect(connection).get_check_constraints("intervention")
    assert constraints == [{
        "name": "ck_intervention_result",
        "sqltext": "result IN (" + ", ".join(repr(value) for value in revision.RESULTS) + ")",
    }]
    revision.downgrade()
    assert snapshot(connection) == before
    revision.upgrade()
    assert connection.exec_driver_sql("SELECT result FROM intervention").all() == [(None,), (None,)]


@pytest.mark.parametrize("result", [
    "RESOLVED", "PARTIALLY_RESOLVED", "UNRESOLVED",
    "PART_NEEDED", "QUOTE_NEEDED", "RESCHEDULE",
])
def test_valid_results_and_read_only_downgrade_guard(legacy, result):
    connection, revision = legacy
    revision.upgrade()
    connection.execute(sa.text("UPDATE intervention SET result=:result WHERE id=1"), {"result": result})
    before = snapshot(connection)
    with pytest.raises(RuntimeError, match="id=1"):
        revision.downgrade()
    assert snapshot(connection) == before


@pytest.mark.parametrize("result", ["", "resolved", "UNKNOWN", " RESOLVED"])
def test_invalid_results_rejected(legacy, result):
    connection, revision = legacy
    revision.upgrade()
    with pytest.raises(sa.exc.IntegrityError):
        connection.execute(sa.text("UPDATE intervention SET result=:result WHERE id=1"), {"result": result})


def test_empty_roundtrip(legacy):
    connection, revision = legacy
    connection.exec_driver_sql("DELETE FROM intervention")
    before = snapshot(connection)
    revision.upgrade()
    revision.downgrade()
    assert snapshot(connection) == before


def test_postgresql_real_chain_roundtrip():
    url = os.environ.get("TERVO_RESULT_MIGRATION_TEST_URL")
    if not url:
        pytest.skip("TERVO_RESULT_MIGRATION_TEST_URL not set (disposable PostgreSQL only)")
    engine = sa.create_engine(url)
    assert engine.dialect.name == "postgresql"
    config = Config()
    config.set_main_option("script_location", str(Path(__file__).parents[1] / "alembic"))
    revisions = list(ScriptDirectory.from_config(config).walk_revisions(base="base", head="i106e0010001"))
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            schema = f"result_test_{uuid4().hex}"
            connection.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
            connection.exec_driver_sql(f'SET LOCAL search_path TO "{schema}"')
            with Operations.context(MigrationContext.configure(connection)):
                for revision in reversed(revisions):
                    revision.module.upgrade()
                column = next(c for c in sa.inspect(connection).get_columns("intervention") if c["name"] == "result")
                assert column["nullable"] and column["default"] is None
                assert any(c["name"] == "ck_intervention_result"
                           for c in sa.inspect(connection).get_check_constraints("intervention"))
                revisions[0].module.downgrade()
                assert "result" not in {c["name"] for c in sa.inspect(connection).get_columns("intervention")}
                revisions[0].module.upgrade()
                for revision in revisions:
                    revision.module.downgrade()
                assert sa.inspect(connection).get_table_names() == []
        finally:
            transaction.rollback()
    engine.dispose()
