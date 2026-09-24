"""Link interventions to sites, preserving existing client history."""
from alembic import op
import sqlalchemy as sa

revision = "06c3c51d3e72"
down_revision = "24556984074e"
branch_labels = None
depends_on = None


def upgrade():
    # Create one default site per legacy client that has interventions but no site.
    op.execute("""
        INSERT INTO site (client_id, name, address, postal_code, city)
        SELECT c.id, 'Site principal', c.address, c.postal_code, c.city
        FROM client c
        WHERE EXISTS (SELECT 1 FROM intervention i WHERE i.client_id = c.id)
          AND NOT EXISTS (SELECT 1 FROM site s WHERE s.client_id = c.id)
    """)
    op.add_column("intervention", sa.Column("site_id", sa.Integer(), nullable=True))
    op.execute("""
        UPDATE intervention SET site_id = (
            SELECT MIN(s.id) FROM site s WHERE s.client_id = intervention.client_id
        )
    """)
    op.alter_column("intervention", "site_id", nullable=False)
    op.create_foreign_key("intervention_site_id_fkey", "intervention", "site", ["site_id"], ["id"], ondelete="CASCADE")
    op.create_index("ix_intervention_site_id", "intervention", ["site_id"])
    op.drop_index("ix_intervention_client_id", table_name="intervention")
    op.drop_constraint("job_client_id_fkey", "intervention", type_="foreignkey")
    op.drop_column("intervention", "client_id")


def downgrade():
    op.add_column("intervention", sa.Column("client_id", sa.Integer(), nullable=True))
    op.execute("""
        UPDATE intervention SET client_id = (
            SELECT s.client_id FROM site s WHERE s.id = intervention.site_id
        )
    """)
    op.alter_column("intervention", "client_id", nullable=False)
    op.create_foreign_key("job_client_id_fkey", "intervention", "client", ["client_id"], ["id"], ondelete="CASCADE")
    op.create_index("ix_intervention_client_id", "intervention", ["client_id"])
    op.drop_index("ix_intervention_site_id", table_name="intervention")
    op.drop_constraint("intervention_site_id_fkey", "intervention", type_="foreignkey")
    op.drop_column("intervention", "site_id")
