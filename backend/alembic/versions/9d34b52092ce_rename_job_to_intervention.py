"""rename job to intervention

Revision ID: 9d34b52092ce
Revises: add2e3d9afdc
Create Date: 2026-09-23 19:37:34.456797

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9d34b52092ce"
down_revision: Union[str, Sequence[str], None] = "add2e3d9afdc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Rename `job` → `intervention` (table, enum, colonnes FK, index) + under_warranty."""
    # 1. Enum `jobstatus` → `interventionstatus` (valeurs français → anglais).
    op.execute("ALTER TYPE jobstatus RENAME TO interventionstatus")
    op.execute("ALTER TYPE interventionstatus RENAME VALUE 'planifié' TO 'PLANNED'")
    op.execute("ALTER TYPE interventionstatus RENAME VALUE 'en_cours' TO 'IN_PROGRESS'")
    op.execute("ALTER TYPE interventionstatus RENAME VALUE 'terminé' TO 'COMPLETED'")
    op.execute("ALTER TYPE interventionstatus RENAME VALUE 'annulé' TO 'CANCELLED'")

    # 2. Table principale.
    op.rename_table("job", "intervention")
    op.add_column(
        "intervention",
        sa.Column("under_warranty", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )

    # 3. Table photo + colonnes FK `job_id` → `intervention_id`.
    op.rename_table("job_photo", "intervention_photo")
    op.alter_column("checklist_item", "job_id", new_column_name="intervention_id")
    op.alter_column("intervention_photo", "job_id", new_column_name="intervention_id")
    op.alter_column("material", "job_id", new_column_name="intervention_id")
    op.alter_column("review", "job_id", new_column_name="intervention_id")

    # 4. Index de la table `intervention`.
    op.execute("ALTER INDEX ix_job_client_id RENAME TO ix_intervention_client_id")
    op.execute("ALTER INDEX ix_job_id RENAME TO ix_intervention_id")
    op.execute("ALTER INDEX ix_job_priority RENAME TO ix_intervention_priority")
    op.execute("ALTER INDEX ix_job_scheduled_date RENAME TO ix_intervention_scheduled_date")
    op.execute("ALTER INDEX ix_job_status RENAME TO ix_intervention_status")
    op.execute("ALTER INDEX ix_job_technician_id RENAME TO ix_intervention_technician_id")

    # 5. Index des tables filles.
    op.execute("ALTER INDEX ix_job_photo_id RENAME TO ix_intervention_photo_id")
    op.execute("ALTER INDEX ix_job_photo_job_id RENAME TO ix_intervention_photo_intervention_id")
    op.execute("ALTER INDEX ix_material_job_id RENAME TO ix_material_intervention_id")
    op.execute("ALTER INDEX ix_checklist_item_job_id RENAME TO ix_checklist_item_intervention_id")
    op.execute("ALTER INDEX ix_review_job_id RENAME TO ix_review_intervention_id")


def downgrade() -> None:
    """Inverse du rename : `intervention` → `job`."""
    # 5. Index des tables filles.
    op.execute("ALTER INDEX ix_review_intervention_id RENAME TO ix_review_job_id")
    op.execute("ALTER INDEX ix_checklist_item_intervention_id RENAME TO ix_checklist_item_job_id")
    op.execute("ALTER INDEX ix_material_intervention_id RENAME TO ix_material_job_id")
    op.execute("ALTER INDEX ix_intervention_photo_intervention_id RENAME TO ix_job_photo_job_id")
    op.execute("ALTER INDEX ix_intervention_photo_id RENAME TO ix_job_photo_id")

    # 4. Index de la table `intervention`.
    op.execute("ALTER INDEX ix_intervention_technician_id RENAME TO ix_job_technician_id")
    op.execute("ALTER INDEX ix_intervention_status RENAME TO ix_job_status")
    op.execute("ALTER INDEX ix_intervention_scheduled_date RENAME TO ix_job_scheduled_date")
    op.execute("ALTER INDEX ix_intervention_priority RENAME TO ix_job_priority")
    op.execute("ALTER INDEX ix_intervention_id RENAME TO ix_job_id")
    op.execute("ALTER INDEX ix_intervention_client_id RENAME TO ix_job_client_id")

    # 3. Colonnes FK + table photo.
    op.alter_column("review", "intervention_id", new_column_name="job_id")
    op.alter_column("material", "intervention_id", new_column_name="job_id")
    op.alter_column("intervention_photo", "intervention_id", new_column_name="job_id")
    op.alter_column("checklist_item", "intervention_id", new_column_name="job_id")
    op.rename_table("intervention_photo", "job_photo")

    # 2. Table principale.
    op.drop_column("intervention", "under_warranty")
    op.rename_table("intervention", "job")

    # 1. Enum.
    op.execute("ALTER TYPE interventionstatus RENAME VALUE 'CANCELLED' TO 'annulé'")
    op.execute("ALTER TYPE interventionstatus RENAME VALUE 'COMPLETED' TO 'terminé'")
    op.execute("ALTER TYPE interventionstatus RENAME VALUE 'IN_PROGRESS' TO 'en_cours'")
    op.execute("ALTER TYPE interventionstatus RENAME VALUE 'PLANNED' TO 'planifié'")
    op.execute("ALTER TYPE interventionstatus RENAME TO jobstatus")
