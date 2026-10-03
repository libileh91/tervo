"""Explicit intervention outcome (INT-106); historical outcomes remain unknown."""
import sqlalchemy as sa
from alembic import op

revision = "i106e0010001"
down_revision = "h105e0010001"
branch_labels = None
depends_on = None

RESULTS = (
    "RESOLVED", "PARTIALLY_RESOLVED", "UNRESOLVED",
    "PART_NEEDED", "QUOTE_NEEDED", "RESCHEDULE",
)


def upgrade():
    with op.batch_alter_table("intervention") as batch:
        batch.add_column(sa.Column("result", sa.String(30), nullable=True))
        batch.create_check_constraint(
            "ck_intervention_result",
            "result IN (" + ", ".join(repr(value) for value in RESULTS) + ")",
        )


def downgrade():
    # Refuse data loss before even entering the DDL batch.
    row = op.get_bind().execute(sa.text(
        "SELECT id FROM intervention WHERE result IS NOT NULL ORDER BY id LIMIT 1"
    )).first()
    if row is not None:
        raise RuntimeError(f"INT-106 downgrade refused result at id={row.id}")
    with op.batch_alter_table("intervention") as batch:
        batch.drop_constraint("ck_intervention_result", type_="check")
        batch.drop_column("result")
