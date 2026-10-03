"""Targeted SQLite migration and full PostgreSQL chain, on disposable schemas only."""
import os
from pathlib import Path
from uuid import uuid4
import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from app.config import settings
from app.core.base import Base
from app.model_registry import load_models

PREVIOUS = "d100e0010001"
REVISION = "e103e0010001"
HEAD = "h105e0010001"
BACKEND = Path(__file__).resolve().parents[1]


@pytest.fixture
def migration(tmp_path, monkeypatch):
    load_models()
    postgres = os.environ.get("TERVO_INSTALLATION_MIGRATION_TEST_URL")
    schema = "installation_migration_" + uuid4().hex
    admin = None
    if postgres:
        admin = sa.create_engine(postgres)
        with admin.begin() as db:
            db.execute(sa.text(f'CREATE SCHEMA {schema}'))
        monkeypatch.setenv("PGOPTIONS", f"-csearch_path={schema}")
        url = postgres
    else:
        url = f"sqlite:///{tmp_path / 'migration.db'}"
    monkeypatch.setattr(settings, "DATABASE_URL", url)
    config = Config(str(BACKEND / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND / "alembic"))
    engine = sa.create_engine(url)
    if postgres:
        command.upgrade(config, PREVIOUS)
    else:
        # The old rename migration uses PostgreSQL ALTER TYPE. Reconstruct only
        # the previous schema for SQLite; the full chain is tested on PostgreSQL.
        previous = sa.MetaData()
        for table in Base.metadata.sorted_tables:
            if table.name not in {"installation", "sale", "sale_line",
                                  "checklist_template", "intervention_checklist", "checklist_item",
                                  "photo", "material_usage"}:
                table.to_metadata(previous)
        sa.Table("intervention_photo", previous,
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("intervention_id", sa.Integer(),
                      sa.ForeignKey("intervention.id", ondelete="CASCADE"),
                      nullable=False, index=True),
            sa.Column("category", sa.String(20), nullable=False),
            sa.Column("file_path", sa.String(500), nullable=False),
            sa.Column("thumbnail_path", sa.String(500)),
            sa.Column("taken_at", sa.DateTime(), server_default=sa.func.now(), nullable=False))
        sa.Table("material", previous,
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("intervention_id", sa.Integer(),
                      sa.ForeignKey("intervention.id", ondelete="CASCADE"),
                      nullable=False, index=True),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("quantity", sa.String(50)),
            sa.Column("position", sa.Integer(), nullable=False))
        # Reconstruct the checklist that actually existed at PREVIOUS, rather
        # than leaking current tables into a stamped historical schema.
        sa.Table("checklist_item", previous,
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("intervention_id", sa.Integer(),
                      sa.ForeignKey("intervention.id", ondelete="CASCADE"),
                      nullable=False, index=True),
            sa.Column("category", sa.String(20), nullable=False),
            sa.Column("label", sa.String(255), nullable=False),
            sa.Column("checked", sa.Boolean(), nullable=False),
            sa.Column("note", sa.Text()),
            sa.Column("position", sa.Integer(), nullable=False))
        equipment = previous.tables["equipment"]
        for constraint in list(equipment.constraints):
            if isinstance(constraint, (sa.ForeignKeyConstraint, sa.UniqueConstraint)) and list(constraint.columns.keys()) == ["installation_id"]:
                equipment.constraints.remove(constraint)
                if isinstance(constraint, sa.ForeignKeyConstraint):
                    for fk in constraint.elements:
                        equipment.foreign_keys.remove(fk)
                        equipment.c.installation_id.foreign_keys.remove(fk)
        previous.create_all(engine)
        command.stamp(config, PREVIOUS)
    with engine.begin() as db:
        db.execute(sa.text("INSERT INTO client (id,full_name,phone,address) VALUES (1,'Historical','0102030405','Paris')"))
        db.execute(sa.text("INSERT INTO site (id,client_id,name,address) VALUES (1,1,'Home','Paris')"))
        db.execute(sa.text("INSERT INTO equipment (id,site_id,serial_number,notes) VALUES (1,1,'HISTORIC','Keep history')"))
        db.execute(sa.text("INSERT INTO equipment (id,site_id,replaced_by_id) VALUES (2,1,1)"))
    try:
        yield config, engine
    finally:
        engine.dispose()
        if admin is not None:
            with admin.begin() as db:
                db.execute(sa.text(f'DROP SCHEMA {schema} CASCADE'))
            admin.dispose()


def test_upgrade_preserves_history_and_enforces_constraints(migration):
    config, engine = migration
    command.upgrade(config, "head")
    inspector = sa.inspect(engine)
    assert any(c['name'] == 'sale_line_id' and c['nullable'] for c in inspector.get_columns('installation'))
    assert 'sale' in inspector.get_table_names() and 'sale_line' in inspector.get_table_names()
    assert any(f['referred_table']=='installation' for f in inspector.get_foreign_keys('equipment'))
    assert any(u['column_names']==['installation_id'] for u in inspector.get_unique_constraints('equipment'))
    with engine.connect() as db:
        if engine.dialect.name == 'sqlite':
            db.execute(sa.text("PRAGMA foreign_keys=ON"))
        assert db.execute(sa.text("SELECT serial_number,notes,installation_id FROM equipment WHERE id=1")).one() == ('HISTORIC','Keep history',None)
        assert db.scalar(sa.text("SELECT replaced_by_id FROM equipment WHERE id=2")) == 1
        if engine.dialect.name == 'sqlite':
            assert db.execute(sa.text("PRAGMA foreign_key_check")).all() == []
        db.commit()
        db.execute(sa.text("INSERT INTO installation (id,site_id) VALUES (1,1)"))
        db.execute(sa.text("UPDATE equipment SET installation_id=1 WHERE id=1"))
        db.commit()
        for sql in (
            "UPDATE equipment SET installation_id=999 WHERE id=2",
            "UPDATE equipment SET installation_id=1 WHERE id=2",
            "DELETE FROM installation WHERE id=1",
            "DELETE FROM site WHERE id=1",
            "UPDATE installation SET status='PLANNED' WHERE id=1",
            "INSERT INTO installation (id) VALUES (2)",
        ):
            with pytest.raises(sa.exc.IntegrityError):
                db.execute(sa.text(sql))
            db.rollback()
    with pytest.raises(RuntimeError, match="downgrade destructif refusé"):
        command.downgrade(config, PREVIOUS)
    assert 'installation' in sa.inspect(engine).get_table_names()


def test_empty_round_trip_preserves_existing_equipment(migration):
    config, engine = migration
    command.upgrade(config, "head")
    command.downgrade(config, PREVIOUS)
    assert "installation" not in sa.inspect(engine).get_table_names()
    command.upgrade(config, "head")
    with engine.connect() as db:
        assert db.scalar(sa.text("SELECT COUNT(*) FROM equipment")) == 2
        assert db.scalar(sa.text("SELECT version_num FROM alembic_version")) == HEAD
        assert db.scalar(sa.text("SELECT COUNT(*) FROM equipment WHERE installation_id IS NOT NULL")) == 0


def test_unverifiable_legacy_ids_fail_without_erasing_data(migration):
    config, engine = migration
    with engine.begin() as db:
        db.execute(sa.text("UPDATE equipment SET installation_id=123 WHERE id=1"))
    with pytest.raises(RuntimeError, match="arbitrage manuel requis"):
        command.upgrade(config, "head")
    assert 'installation' not in sa.inspect(engine).get_table_names()
    with engine.connect() as db:
        assert db.scalar(sa.text("SELECT installation_id FROM equipment WHERE id=1")) == 123
        assert db.scalar(sa.text("SELECT version_num FROM alembic_version")) == PREVIOUS
