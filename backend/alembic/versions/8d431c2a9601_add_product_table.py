"""Add commercial product catalogue.

Revision ID: 8d431c2a9601
Revises: 06c3c51d3e72
"""
from alembic import op
import sqlalchemy as sa

revision = "8d431c2a9601"
down_revision = "06c3c51d3e72"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("product",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("reference", sa.String(100), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("brand", sa.String(255), nullable=False),
        sa.Column("model", sa.String(255), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("characteristics", sa.JSON(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("reference"))
    for column in ("id", "brand", "category"):
        op.create_index(f"ix_product_{column}", "product", [column])


def downgrade():
    op.drop_table("product")
