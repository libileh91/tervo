"""INT-105 migration against disposable legacy databases, never application DB."""
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
    path = Path(__file__).parents[1] / "alembic/versions/h105e0010001_media_usage.py"
    spec = importlib.util.spec_from_file_location("media_revision", path)
    revision = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(revision)
    engine = sa.create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        connection.exec_driver_sql("CREATE TABLE intervention (id INTEGER PRIMARY KEY)")
        connection.exec_driver_sql(
            "CREATE TABLE intervention_photo (id INTEGER PRIMARY KEY, intervention_id INTEGER NOT NULL "
            ", category VARCHAR(20) NOT NULL, "
            "file_path VARCHAR(500) NOT NULL, thumbnail_path VARCHAR(500), "
            "taken_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, "
            "FOREIGN KEY(intervention_id) REFERENCES intervention(id) ON DELETE CASCADE)")
        connection.exec_driver_sql(
            "CREATE TABLE material (id INTEGER PRIMARY KEY, intervention_id INTEGER NOT NULL "
            ", name VARCHAR(255) NOT NULL, "
            "quantity VARCHAR(50), position INTEGER NOT NULL, "
            "FOREIGN KEY(intervention_id) REFERENCES intervention(id) ON DELETE CASCADE)")
        for table in ("intervention_photo", "material"):
            for column in ("id", "intervention_id"):
                connection.exec_driver_sql(f"CREATE INDEX ix_{table}_{column} ON {table}({column})")
        connection.exec_driver_sql("INSERT INTO intervention VALUES (1), (2)")
        connection.exec_driver_sql(
            "INSERT INTO intervention_photo VALUES (7, 1, 'avant', '/original', '/thumb', '2026-01-01')")
        connection.exec_driver_sql("INSERT INTO material VALUES (9, 1, 'Pièce', '02.00', 4)")
        revision.op = Operations(MigrationContext.configure(connection))
        yield connection, revision
    engine.dispose()


def snapshot(connection):
    tables = sorted(sa.inspect(connection).get_table_names())
    return [(table, connection.exec_driver_sql(f"SELECT * FROM {table} ORDER BY id").all(),
             [(c["name"], str(c["type"]), c["nullable"], c["default"])
              for c in sa.inspect(connection).get_columns(table)],
             sa.inspect(connection).get_indexes(table)) for table in tables]


def test_semantic_roundtrip_and_schema(legacy):
    connection, revision = legacy
    revision.upgrade()
    assert connection.exec_driver_sql("SELECT * FROM photo").one() == (
        7, 1, "BEFORE", "/original", "/thumb", "2026-01-01")
    assert connection.exec_driver_sql("SELECT * FROM material_usage").one() == (9, 1, "Pièce", 2, 4, None)
    for table in ("photo", "material_usage"):
        assert {i["name"] for i in sa.inspect(connection).get_indexes(table)} == {
            f"ix_{table}_id", f"ix_{table}_intervention_id"}
        assert sa.inspect(connection).get_foreign_keys(table)[0]["options"]["ondelete"] == "CASCADE"
    revision.downgrade()
    assert connection.exec_driver_sql("SELECT quantity FROM material").scalar_one() == "2"
    revision.upgrade()
    assert connection.exec_driver_sql("SELECT quantity, unit FROM material_usage").one() == (2, None)


@pytest.mark.parametrize("quantity", ["0", "-1", "NaN", "Infinity", "1,2", "1 kg", "1.0001", "1000000000", "1e2"])
def test_quantity_preflight_is_read_only(legacy, quantity):
    connection, revision = legacy
    connection.execute(sa.text("UPDATE material SET quantity=:q"), {"q": quantity})
    before = snapshot(connection)
    with pytest.raises(RuntimeError, match="id=9"):
        revision.upgrade()
    assert snapshot(connection) == before


def test_category_preflight_is_read_only(legacy):
    connection, revision = legacy
    connection.exec_driver_sql("UPDATE intervention_photo SET category='unknown'")
    before = snapshot(connection)
    with pytest.raises(RuntimeError, match="id=7"):
        revision.upgrade()
    assert snapshot(connection) == before


@pytest.mark.parametrize("quantity", [None, "", "   ", "999999999.999", ".125"])
def test_valid_quantities(legacy, quantity):
    connection, revision = legacy
    connection.execute(sa.text("UPDATE material SET quantity=:q"), {"q": quantity})
    revision.upgrade()
    value, unit = connection.exec_driver_sql("SELECT quantity, unit FROM material_usage").one()
    assert unit is None
    assert value is None if quantity is None or not quantity.strip() else value == float(quantity)


@pytest.mark.parametrize("category,usage", [
    ("avant", "BEFORE"), ("après", "AFTER"), ("apres", "AFTER"),
    *[(value, value) for value in ("BEFORE", "AFTER", "EQUIPMENT", "ANOMALY", "PART", "OTHER")],
])
def test_categories(legacy, category, usage):
    connection, revision = legacy
    connection.execute(sa.text("UPDATE intervention_photo SET category=:c"), {"c": category})
    revision.upgrade()
    assert connection.exec_driver_sql("SELECT usage FROM photo").scalar_one() == usage


@pytest.mark.parametrize("statement", [
    "UPDATE photo SET usage='OTHER'", "UPDATE material_usage SET unit=''",
    "UPDATE material_usage SET unit='kg'",
])
def test_downgrade_guard_is_read_only(legacy, statement):
    connection, revision = legacy
    revision.upgrade()
    connection.exec_driver_sql(statement)
    before = snapshot(connection)
    with pytest.raises(RuntimeError, match="id="):
        revision.downgrade()
    assert snapshot(connection) == before


@pytest.mark.parametrize("statement", [
    "UPDATE photo SET usage='unknown'", "UPDATE material_usage SET quantity=0",
    "UPDATE material_usage SET quantity=-1", "UPDATE photo SET intervention_id=999",
])
def test_constraints(legacy, statement):
    connection, revision = legacy
    revision.upgrade()
    with pytest.raises(sa.exc.IntegrityError):
        connection.exec_driver_sql(statement)


def test_parent_cascade(legacy):
    connection, revision = legacy
    revision.upgrade()
    connection.exec_driver_sql("DELETE FROM intervention WHERE id=1")
    assert connection.exec_driver_sql("SELECT count(*) FROM photo").scalar_one() == 0
    assert connection.exec_driver_sql("SELECT count(*) FROM material_usage").scalar_one() == 0
    assert connection.exec_driver_sql("SELECT id FROM intervention").all() == [(2,)]


def test_postgresql_real_chain_roundtrip():
    url = os.environ.get("TERVO_MEDIA_MIGRATION_TEST_URL")
    if not url:
        pytest.skip("TERVO_MEDIA_MIGRATION_TEST_URL not set (disposable PostgreSQL only)")
    engine = sa.create_engine(url)
    assert engine.dialect.name == "postgresql"
    config = Config()
    config.set_main_option("script_location", str(Path(__file__).parents[1] / "alembic"))
    revisions = list(ScriptDirectory.from_config(config).walk_revisions(base="base", head="h105e0010001"))
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            schema = f"media_test_{uuid4().hex}"
            connection.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
            connection.exec_driver_sql(f'SET LOCAL search_path TO "{schema}"')
            with Operations.context(MigrationContext.configure(connection)):
                for revision in reversed(revisions):
                    revision.module.upgrade()
                assert "photo" in sa.inspect(connection).get_table_names()
                revisions[0].module.downgrade()
                assert "intervention_photo" in sa.inspect(connection).get_table_names()
                revisions[0].module.upgrade()
                for revision in revisions:
                    revision.module.downgrade()
                assert sa.inspect(connection).get_table_names() == []
        finally:
            transaction.rollback()
    engine.dispose()
