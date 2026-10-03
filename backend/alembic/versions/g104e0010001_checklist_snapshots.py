"""Versioned checklist snapshots, preserving all historical items (INT-104)."""
from alembic import op
import sqlalchemy as sa

revision = "g104e0010001"
down_revision = "f102e0010001"
branch_labels = None
depends_on = None

_NAMING = {"fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s"}


def _item_fk(column):
    """Handle both PostgreSQL's historical name and unnamed SQLite fixtures."""
    for fk in sa.inspect(op.get_bind()).get_foreign_keys("checklist_item"):
        if fk["constrained_columns"] == [column]:
            return fk["name"] or f"fk_checklist_item_{column}_{fk['referred_table']}"
    raise RuntimeError(f"Missing checklist_item foreign key: {column}")


def upgrade():
    op.create_table(
        "checklist_template",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("intervention_type", sa.String(100), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("items", sa.JSON(), nullable=False),
        sa.CheckConstraint("version >= 1", name="ck_checklist_template_version"),
    )
    op.create_table(
        "intervention_checklist",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("intervention_id", sa.Integer(), sa.ForeignKey("intervention.id", ondelete="CASCADE"), nullable=False),
        sa.Column("template_id", sa.Integer(), sa.ForeignKey("checklist_template.id", ondelete="RESTRICT")),
        sa.Column("template_name", sa.String(255), nullable=False),
        sa.Column("template_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("intervention_id"),
        sa.CheckConstraint("template_version >= 1", name="ck_intervention_checklist_template_version"),
    )
    # A snapshot exists even for interventions with no historical controls.
    op.execute(sa.text(
        "INSERT INTO intervention_checklist (intervention_id, template_name, template_version) "
        "SELECT id, 'Checklist historique', 1 FROM intervention"
    ))
    with op.batch_alter_table("checklist_item") as batch:
        batch.add_column(sa.Column("intervention_checklist_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("result", sa.String(100), nullable=True))
        batch.add_column(sa.Column("completed_at", sa.DateTime(), nullable=True))
    op.execute(sa.text(
        "UPDATE checklist_item SET intervention_checklist_id = "
        "(SELECT id FROM intervention_checklist WHERE intervention_id = checklist_item.intervention_id), "
        "result = CASE WHEN checked THEN 'OK' ELSE NULL END"
    ))
    old_fk = _item_fk("intervention_id")
    with op.batch_alter_table("checklist_item", naming_convention=_NAMING) as batch:
        batch.drop_constraint(old_fk, type_="foreignkey")
        batch.drop_index("ix_checklist_item_intervention_id")
        batch.drop_column("intervention_id")
        batch.drop_column("checked")
        batch.alter_column("note", new_column_name="comment", existing_type=sa.Text())
        batch.alter_column("intervention_checklist_id", nullable=False, existing_type=sa.Integer())
        batch.create_foreign_key("fk_checklist_item_snapshot",
                                 "intervention_checklist", ["intervention_checklist_id"], ["id"], ondelete="CASCADE")
        batch.create_index("ix_checklist_item_intervention_checklist_id", ["intervention_checklist_id"])


def downgrade():
    bind = op.get_bind()
    # Validate before any DDL: the legacy schema cannot represent business metadata.
    checks = (
        ("SELECT id FROM checklist_template LIMIT 1", "checklist templates"),
        ("SELECT id FROM intervention_checklist WHERE template_id IS NOT NULL "
         "OR template_name <> 'Checklist historique' OR template_version <> 1 LIMIT 1", "snapshot provenance"),
        ("SELECT id FROM checklist_item WHERE result IS NOT NULL AND result <> 'OK' LIMIT 1", "checklist results"),
        ("SELECT id FROM checklist_item WHERE completed_at IS NOT NULL LIMIT 1", "completion timestamps"),
    )
    for query, reason in checks:
        if bind.execute(sa.text(query)).first():
            raise RuntimeError(f"INT-104 downgrade refused: would lose {reason}")
    with op.batch_alter_table("checklist_item") as batch:
        batch.add_column(sa.Column("intervention_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("checked", sa.Boolean(), nullable=True))
    op.execute(sa.text(
        "UPDATE checklist_item SET intervention_id = "
        "(SELECT intervention_id FROM intervention_checklist WHERE id = checklist_item.intervention_checklist_id), "
        "checked = CASE WHEN result = 'OK' THEN true ELSE false END"
    ))
    with op.batch_alter_table("checklist_item", naming_convention=_NAMING) as batch:
        batch.drop_constraint(_item_fk("intervention_checklist_id"), type_="foreignkey")
        batch.drop_index("ix_checklist_item_intervention_checklist_id")
        batch.drop_column("intervention_checklist_id")
        batch.drop_column("result")
        batch.drop_column("completed_at")
        batch.alter_column("comment", new_column_name="note", existing_type=sa.Text())
        batch.alter_column("intervention_id", nullable=False, existing_type=sa.Integer())
        batch.alter_column("checked", nullable=False, existing_type=sa.Boolean())
        batch.create_foreign_key("checklist_item_job_id_fkey", "intervention", ["intervention_id"], ["id"], ondelete="CASCADE")
        batch.create_index("ix_checklist_item_intervention_id", ["intervention_id"])
    op.drop_table("intervention_checklist")
    op.drop_table("checklist_template")
