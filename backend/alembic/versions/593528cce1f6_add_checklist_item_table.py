"""add checklist_item table

Revision ID: 593528cce1f6
Revises: 7e7c3408ecfb
Create Date: 2026-06-05 19:58:53.394245

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "593528cce1f6"
down_revision: Union[str, Sequence[str], None] = "7e7c3408ecfb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add checklist_item table."""
    op.create_table(
        "checklist_item",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(length=20), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("checked", sa.Boolean(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["job.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_checklist_item_id"), "checklist_item", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_checklist_item_job_id"), "checklist_item", ["job_id"], unique=False
    )


def downgrade() -> None:
    """Drop checklist_item table."""
    op.drop_index(op.f("ix_checklist_item_job_id"), table_name="checklist_item")
    op.drop_index(op.f("ix_checklist_item_id"), table_name="checklist_item")
    op.drop_table("checklist_item")
