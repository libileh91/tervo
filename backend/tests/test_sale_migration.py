"""INT-102 migration on a disposable SQLite schema."""
import importlib.util
from pathlib import Path
import sqlalchemy as sa
import pytest
from sqlalchemy.exc import IntegrityError
from alembic.migration import MigrationContext
from alembic.operations import Operations


@pytest.fixture

def revision():
    path = Path(__file__).parents[1] / "alembic/versions/f102e0010001_add_sales.py"
    spec = importlib.util.spec_from_file_location("sales_revision", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_sales_migration_preserves_autonomous_installations(revision):
    engine = sa.create_engine("sqlite:///:memory:")
    metadata = sa.MetaData()
    sa.Table("client", metadata, sa.Column("id", sa.Integer, primary_key=True))
    sa.Table("site", metadata, sa.Column("id", sa.Integer, primary_key=True),
             sa.Column("client_id", sa.Integer, sa.ForeignKey("client.id")))
    sa.Table("product", metadata, sa.Column("id", sa.Integer, primary_key=True))
    sa.Table("installation", metadata, sa.Column("id", sa.Integer, primary_key=True),
             sa.Column("site_id", sa.Integer, sa.ForeignKey("site.id")))
    with engine.begin() as connection:
        metadata.create_all(connection)
        connection.execute(sa.text("INSERT INTO client (id) VALUES (1)"))
        connection.execute(sa.text("INSERT INTO site (id, client_id) VALUES (1, 1)"))
        connection.execute(sa.text("INSERT INTO installation (id, site_id) VALUES (1, 1)"))
        revision.op = Operations(MigrationContext.configure(connection))
        revision.upgrade()
        assert connection.execute(sa.text("SELECT sale_line_id FROM installation WHERE id=1")).scalar_one() is None
        assert "sale" in sa.inspect(connection).get_table_names()
        with pytest.raises(IntegrityError):
            connection.execute(sa.text("INSERT INTO sale_line (sale_id, product_id, quantity, unit_price) VALUES (1, 1, 0, 0)"))
        revision.downgrade()
        assert "sale" not in sa.inspect(connection).get_table_names()
        assert "sale_line_id" not in {column["name"] for column in sa.inspect(connection).get_columns("installation")}
