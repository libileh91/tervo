"""Commercial sales and nullable installation provenance (INT-102 / TD-B017)."""
from alembic import op
import sqlalchemy as sa

revision = "f102e0010001"
down_revision = "e103e0010001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("sale",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("client.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("site_id", sa.Integer(), sa.ForeignKey("site.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("sale_date", sa.Date(), nullable=False),
        sa.Column("status", sa.Enum("DRAFT", "CONFIRMED", "CANCELLED", name="sale_status", native_enum=False, create_constraint=True), nullable=False, server_default="DRAFT"),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()))
    for col in ("id", "client_id", "site_id", "status"):
        op.create_index(f"ix_sale_{col}", "sale", [col])
    op.create_table("sale_line",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sale_id", sa.Integer(), sa.ForeignKey("sale.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("product.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("description", sa.String(500)),
        sa.CheckConstraint("quantity > 0", name="ck_sale_line_quantity_positive"),
        sa.CheckConstraint("unit_price >= 0", name="ck_sale_line_price_nonnegative"))
    for col in ("id", "sale_id", "product_id"):
        op.create_index(f"ix_sale_line_{col}", "sale_line", [col])
    with op.batch_alter_table("installation") as batch:
        batch.add_column(sa.Column("sale_line_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_installation_sale_line", "sale_line", ["sale_line_id"], ["id"], ondelete="RESTRICT")
        batch.create_index("ix_installation_sale_line_id", ["sale_line_id"])


def downgrade():
    if op.get_bind().execute(sa.text("SELECT id FROM installation WHERE sale_line_id IS NOT NULL LIMIT 1")).first():
        raise RuntimeError("Installations commerciales présentes : downgrade destructif refusé")
    with op.batch_alter_table("installation") as batch:
        batch.drop_index("ix_installation_sale_line_id")
        batch.drop_constraint("fk_installation_sale_line", type_="foreignkey")
        batch.drop_column("sale_line_id")
    op.drop_table("sale_line")
    op.drop_table("sale")
