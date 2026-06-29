"""add review table

Revision ID: add2e3d9afdc
Revises: 170af5c7827f
Create Date: 2026-06-23 12:28:54.673761

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "add2e3d9afdc"
down_revision: Union[str, Sequence[str], None] = "170af5c7827f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "review",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("reviewer_name", sa.String(length=255), nullable=True),
        sa.Column("share_token", sa.String(length=64), nullable=False),
        sa.Column("share_token_expires_at", sa.DateTime(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["job_id"], ["job.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_review_id"), "review", ["id"], unique=False)
    op.create_index(op.f("ix_review_job_id"), "review", ["job_id"], unique=True)
    op.create_index(
        op.f("ix_review_share_token"), "review", ["share_token"], unique=True
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_review_share_token"), table_name="review")
    op.drop_index(op.f("ix_review_job_id"), table_name="review")
    op.drop_index(op.f("ix_review_id"), table_name="review")
    op.drop_table("review")
