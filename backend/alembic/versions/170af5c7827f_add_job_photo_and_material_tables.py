"""add job_photo and material tables

Revision ID: 170af5c7827f
Revises: 593528cce1f6
Create Date: 2026-06-07 19:17:43.521146

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "170af5c7827f"
down_revision: Union[str, Sequence[str], None] = "593528cce1f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add job_photo and material tables."""
    op.create_table(
        "job_photo",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(length=20), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("thumbnail_path", sa.String(length=500), nullable=True),
        sa.Column(
            "taken_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["job_id"], ["job.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_job_photo_id"), "job_photo", ["id"], unique=False)
    op.create_index(op.f("ix_job_photo_job_id"), "job_photo", ["job_id"], unique=False)
    op.create_table(
        "material",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("quantity", sa.String(length=50), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["job.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_material_id"), "material", ["id"], unique=False)
    op.create_index(op.f("ix_material_job_id"), "material", ["job_id"], unique=False)


def downgrade() -> None:
    """Drop job_photo and material tables."""
    op.drop_index(op.f("ix_material_job_id"), table_name="material")
    op.drop_index(op.f("ix_material_id"), table_name="material")
    op.drop_table("material")
    op.drop_index(op.f("ix_job_photo_job_id"), table_name="job_photo")
    op.drop_index(op.f("ix_job_photo_id"), table_name="job_photo")
    op.drop_table("job_photo")
