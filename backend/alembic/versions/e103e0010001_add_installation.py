"""Autonomous installations and verified equipment link (INT-103 / TD-B014)."""
from alembic import op
import sqlalchemy as sa

revision = "e103e0010001"
down_revision = "d100e0010001"
branch_labels = None
depends_on = None


def upgrade():
    # No Installation existed before this revision. Never erase unverifiable IDs
    # or invent installations to make the new FK pass on an existing database.
    connection = op.get_bind()
    if connection.execute(sa.text(
            "SELECT id FROM equipment WHERE installation_id IS NOT NULL LIMIT 1")).first():
        raise RuntimeError("Equipment.installation_id non vérifiable : arbitrage manuel requis avant migration")
    op.create_table("installation",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("site_id", sa.Integer(), sa.ForeignKey("site.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("scheduled_start", sa.DateTime()),
        sa.Column("scheduled_end", sa.DateTime()),
        sa.Column("started_at", sa.DateTime()),
        sa.Column("completed_at", sa.DateTime()),
        sa.Column("installation_date", sa.Date()),
        sa.Column("commissioning_date", sa.Date()),
        sa.Column("status", sa.Enum("SCHEDULED", "IN_PROGRESS", "COMPLETED", "CANCELLED",
            name="installation_status", native_enum=False, create_constraint=True),
            nullable=False, server_default="SCHEDULED"),
        sa.Column("technician_notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()))
    for column in ("id", "site_id", "status"):
        op.create_index(f"ix_installation_{column}", "installation", [column])
    with op.batch_alter_table("equipment") as batch:
        batch.create_foreign_key("equipment_installation_id_fkey", "installation",
                                 ["installation_id"], ["id"], ondelete="RESTRICT")
        batch.create_unique_constraint("uq_equipment_installation_id", ["installation_id"])


def downgrade():
    if op.get_bind().execute(sa.text("SELECT id FROM installation LIMIT 1")).first():
        raise RuntimeError("Installations présentes : downgrade destructif refusé")
    with op.batch_alter_table("equipment") as batch:
        batch.drop_constraint("uq_equipment_installation_id", type_="unique")
        batch.drop_constraint("equipment_installation_id_fkey", type_="foreignkey")
    op.drop_table("installation")
