"""add site table

Revision ID: 24556984074e
Revises: 9d34b52092ce
Create Date: 2026-09-23 20:30:20.844495

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '24556984074e'
down_revision: Union[str, Sequence[str], None] = '9d34b52092ce'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the `site` table."""
    op.create_table(
        "site",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "client_id",
            sa.Integer(),
            sa.ForeignKey("client.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("address", sa.String(length=500), nullable=False),
        sa.Column("postal_code", sa.String(length=20), nullable=True),
        sa.Column("city", sa.String(length=255), nullable=True),
        sa.Column("country", sa.String(length=100), nullable=True),
        sa.Column("access_notes", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_site_id", "site", ["id"], unique=False)
    op.create_index("ix_site_client_id", "site", ["client_id"], unique=False)
    op.create_index("ix_site_name", "site", ["name"], unique=False)
    op.create_index("ix_site_city", "site", ["city"], unique=False)


def downgrade() -> None:
    """Drop the `site` table."""
    op.drop_index("ix_site_city", table_name="site")
    op.drop_index("ix_site_name", table_name="site")
    op.drop_index("ix_site_client_id", table_name="site")
    op.drop_index("ix_site_id", table_name="site")
    op.drop_table("site")
