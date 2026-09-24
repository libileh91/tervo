"""Physical equipment and optional intervention link (INT-97)."""
from alembic import op
import sqlalchemy as sa

revision = "c197e0010001"
down_revision = "8d431c2a9601"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("equipment",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("site_id", sa.Integer(), sa.ForeignKey("site.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("product.id", ondelete="RESTRICT")),
        sa.Column("installation_id", sa.Integer()),
        sa.Column("serial_number", sa.String(255)),
        sa.Column("installed_at", sa.Date()),
        sa.Column("commissioned_at", sa.Date()),
        sa.Column("warranty_start", sa.Date()),
        sa.Column("warranty_end", sa.Date()),
        sa.Column("lifecycle_status", sa.Enum("ACTIVE", "OUT_OF_SERVICE", "REPLACED", "RETIRED",
                  name="equipment_status", native_enum=False, create_constraint=True), nullable=False, server_default="ACTIVE"),
        sa.Column("replaced_by_id", sa.Integer(), sa.ForeignKey("equipment.id", ondelete="RESTRICT")),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()))
    for column in ("id", "site_id", "product_id", "serial_number", "lifecycle_status"):
        op.create_index(f"ix_equipment_{column}", "equipment", [column])
    with op.batch_alter_table("intervention") as batch:
        batch.add_column(sa.Column("equipment_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("intervention_equipment_id_fkey", "equipment", ["equipment_id"], ["id"], ondelete="RESTRICT")
        batch.create_index("ix_intervention_equipment_id", ["equipment_id"])


def downgrade():
    with op.batch_alter_table("intervention") as batch:
        batch.drop_index("ix_intervention_equipment_id")
        batch.drop_constraint("intervention_equipment_id_fkey", type_="foreignkey")
        batch.drop_column("equipment_id")
    op.drop_table("equipment")
