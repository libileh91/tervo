"""Durable import plans, checkpoints, source identities and errors (INT-100)."""
from alembic import op
import sqlalchemy as sa

revision = 'd100e0010001'
down_revision = 'c197e0010001'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('import_batch',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('source_namespace', sa.String(100), nullable=False),
        sa.Column('file_hash', sa.String(64), nullable=False),
        sa.Column('source_bytes', sa.LargeBinary(), nullable=False),
        sa.Column('selections', sa.JSON(), nullable=False),
        sa.Column('source_records', sa.JSON(), nullable=False),
        sa.Column('plan', sa.JSON()), sa.Column('decisions', sa.JSON()),
        sa.Column('plan_token', sa.String(64)), sa.Column('database_snapshot', sa.String(64)),
        sa.Column('revision', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('execution_slot', sa.Integer(), unique=True),
        sa.Column('execution_token', sa.String(32)),
        sa.Column('lease_until', sa.DateTime()),
        sa.Column('imported_by', sa.Integer(), sa.ForeignKey('user.id', ondelete='SET NULL')),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('completed_at', sa.DateTime()),
        sa.UniqueConstraint('source_namespace', 'file_hash', name='uq_import_file'))
    op.create_table('import_record',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('import_batch_id', sa.Integer(), sa.ForeignKey('import_batch.id'), nullable=False),
        sa.Column('row_key', sa.String(300), nullable=False),
        sa.Column('entity_type', sa.String(30), nullable=False),
        sa.Column('entity_id', sa.Integer()), sa.Column('action', sa.String(20), nullable=False),
        sa.Column('source', sa.JSON(), nullable=False),
        sa.Column('original_values', sa.JSON(), nullable=False),
        sa.Column('normalized_values', sa.JSON(), nullable=False),
        sa.Column('decision', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('import_batch_id', 'row_key', name='uq_import_record_row'))
    op.create_index('ix_import_record_import_batch_id', 'import_record', ['import_batch_id'])
    op.create_table('import_reference',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('source_namespace', sa.String(100), nullable=False),
        sa.Column('entity_type', sa.String(30), nullable=False),
        sa.Column('source_id', sa.String(255), nullable=False),
        sa.Column('entity_id', sa.Integer(), nullable=False),
        sa.UniqueConstraint('source_namespace', 'entity_type', 'source_id', name='uq_import_reference'))
    op.create_table('import_error',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('import_batch_id', sa.Integer(), sa.ForeignKey('import_batch.id'), nullable=False),
        sa.Column('revision', sa.Integer(), nullable=False),
        sa.Column('row_key', sa.String(300), nullable=False),
        sa.Column('code', sa.String(80), nullable=False), sa.Column('severity', sa.String(20), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('source', sa.JSON(), nullable=False), sa.Column('original_values', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False))
    op.create_index('ix_import_error_import_batch_id', 'import_error', ['import_batch_id'])


def downgrade():
    for table in ('import_error', 'import_reference', 'import_record', 'import_batch'):
        op.drop_table(table)
