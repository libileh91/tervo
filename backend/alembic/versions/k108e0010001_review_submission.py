"""INT-108: an invitation is not a submitted customer rating."""

import sqlalchemy as sa
from alembic import op

revision = "k108e0010001"
down_revision = "j107e0010001"
branch_labels = None
depends_on = None

RATING_RULE = (
    "(submitted_at IS NULL AND rating IS NULL) OR "
    "(submitted_at IS NOT NULL AND rating BETWEEN 1 AND 5)"
)


def upgrade():
    connection = op.get_bind()
    invalid = connection.execute(sa.text(
        "SELECT id FROM review WHERE submitted_at IS NOT NULL "
        "AND (rating IS NULL OR rating NOT BETWEEN 1 AND 5) LIMIT 1"
    )).first()
    if invalid:
        raise RuntimeError(f"INT-108: invalid submitted rating on review {invalid.id}")
    with op.batch_alter_table("review") as batch:
        batch.alter_column("rating", existing_type=sa.Integer(), nullable=True)
    # Old completion assigned a synthetic 5 to pending invitations. Do not
    # mistake it for a customer rating; keep IDs, tokens and real submissions.
    connection.execute(sa.text("UPDATE review SET rating = NULL WHERE submitted_at IS NULL"))
    with op.batch_alter_table("review") as batch:
        batch.create_check_constraint("ck_review_submission_rating", RATING_RULE)


def downgrade():
    # Reverting a pending invitation to NOT NULL would invent a customer rating.
    pending = op.get_bind().execute(sa.text(
        "SELECT id FROM review WHERE rating IS NULL LIMIT 1"
    )).first()
    if pending:
        raise RuntimeError(f"INT-108 downgrade refused pending review {pending.id}")
    with op.batch_alter_table("review") as batch:
        batch.drop_constraint("ck_review_submission_rating", type_="check")
        batch.alter_column("rating", existing_type=sa.Integer(), nullable=False)
