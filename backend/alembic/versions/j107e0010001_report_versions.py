"""Private transactional PDF archive, preserving every version."""
import sqlalchemy as sa
from alembic import op

revision = "j107e0010001"
down_revision = "i106e0010001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("report",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("intervention_id", sa.Integer(), sa.ForeignKey("intervention.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("intervention_id", name="uq_report_intervention"))
    op.create_table("report_version",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("report_id", sa.Integer(), sa.ForeignKey("report.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("request_key", sa.String(100)),
        sa.Column("pdf", sa.LargeBinary(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("generated_at", sa.DateTime(), nullable=False),
        sa.Column("generated_by_id", sa.Integer(), sa.ForeignKey("user.id", ondelete="SET NULL")),
        sa.Column("transmitted_at", sa.DateTime()),
        sa.Column("transmitted_by_id", sa.Integer(), sa.ForeignKey("user.id", ondelete="SET NULL")),
        sa.UniqueConstraint("report_id", "version", name="uq_report_version_number"),
        sa.UniqueConstraint("report_id", "request_key", name="uq_report_version_request"),
        sa.CheckConstraint("version >= 1", name="ck_report_version_number"),
        sa.CheckConstraint("size > 0", name="ck_report_version_size"))


def downgrade():
    if op.get_bind().execute(sa.text("SELECT id FROM report LIMIT 1")).first():
        raise RuntimeError("INT-107 downgrade refused: archived reports would be lost")
    op.drop_table("report_version")
    op.drop_table("report")
