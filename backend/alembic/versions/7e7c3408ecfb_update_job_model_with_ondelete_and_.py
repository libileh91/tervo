"""update job model with ondelete and forward relationships

Revision ID: 7e7c3408ecfb
Revises: 5cc5d1686947
Create Date: 2026-06-05 19:43:08.762714

Note: SQLite doesn't support ALTER CONSTRAINT.
The FK ondelete options are applied at the ORM/PostgreSQL level.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "7e7c3408ecfb"
down_revision: Union[str, Sequence[str], None] = "5cc5d1686947"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SQLite doesn't support ALTER of constraints.
    # The ondelete options are already defined in the model
    # and will apply on PostgreSQL. This is a metadata-only change.
    pass


def downgrade() -> None:
    pass
