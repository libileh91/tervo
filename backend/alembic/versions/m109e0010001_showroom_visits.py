"""INT-109: showroom visits and presented catalogue references."""

import sqlalchemy as sa
from alembic import op

revision = "m109e0010001"
down_revision = "k108e0010001"
branch_labels = None
depends_on = None

STATUSES = (
    "TO_FOLLOW_UP", "CONSIDERING", "QUOTE_REQUESTED", "QUOTE_SENT",
    "SOLD", "LOST", "NO_FURTHER_ACTION",
)


def upgrade():
    op.create_table(
        "showroom_visit",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("client.id", ondelete="RESTRICT")),
        sa.Column("visitor_name", sa.String(255)),
        sa.Column("visited_at", sa.DateTime(), nullable=False),
        sa.Column("salesperson_id", sa.Integer(), sa.ForeignKey("user.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("follow_up_status", sa.String(30), nullable=False, server_default="TO_FOLLOW_UP"),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "client_id IS NOT NULL OR "
            "(visitor_name IS NOT NULL AND length(trim(visitor_name)) > 0)",
            name="ck_showroom_visit_identity",
        ),
        sa.CheckConstraint(
            "follow_up_status IN (" + ", ".join(repr(status) for status in STATUSES) + ")",
            name="ck_showroom_visit_follow_up_status",
        ),
    )
    for name in ("client_id", "visited_at", "salesperson_id", "follow_up_status"):
        op.create_index(f"ix_showroom_visit_{name}", "showroom_visit", [name])
    op.create_table(
        "showroom_visit_product",
        sa.Column("visit_id", sa.Integer(), sa.ForeignKey("showroom_visit.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("product.id", ondelete="RESTRICT"), primary_key=True),
    )


def downgrade():
    connection = op.get_bind()
    if (connection.execute(sa.text("SELECT id FROM showroom_visit LIMIT 1")).first()
            or connection.execute(sa.text("SELECT visit_id FROM showroom_visit_product LIMIT 1")).first()):
        raise RuntimeError("INT-109 downgrade refused: showroom history would be lost")
    op.drop_table("showroom_visit_product")
    for name in ("follow_up_status", "salesperson_id", "visited_at", "client_id"):
        op.drop_index(f"ix_showroom_visit_{name}", table_name="showroom_visit")
    op.drop_table("showroom_visit")
