"""Technical import journal. Source bytes/plans remain private to administrators."""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, LargeBinary, String, Text, UniqueConstraint, func
from app.models.base import Base


class ImportBatch(Base):
    __tablename__ = 'import_batch'
    __table_args__ = (UniqueConstraint('source_namespace', 'file_hash', name='uq_import_file'),)
    id = Column(Integer, primary_key=True)
    filename = Column(String(255), nullable=False)
    source_namespace = Column(String(100), nullable=False)
    file_hash = Column(String(64), nullable=False)
    source_bytes = Column(LargeBinary, nullable=False)
    selections = Column(JSON, nullable=False)
    source_records = Column(JSON, nullable=False)
    plan = Column(JSON, nullable=True)
    decisions = Column(JSON, nullable=True)
    plan_token = Column(String(64), nullable=True)
    database_snapshot = Column(String(64), nullable=True)
    revision = Column(Integer, nullable=False, default=0)
    status = Column(String(20), nullable=False, default='staged')
    # A unique non-null slot serializes imports across files, including SQLite.
    execution_slot = Column(Integer, nullable=True, unique=True)
    execution_token = Column(String(32), nullable=True)
    lease_until = Column(DateTime, nullable=True)
    imported_by = Column(Integer, ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    completed_at = Column(DateTime, nullable=True)


class ImportRecord(Base):
    __tablename__ = 'import_record'
    __table_args__ = (UniqueConstraint('import_batch_id', 'row_key', name='uq_import_record_row'),)
    id = Column(Integer, primary_key=True)
    import_batch_id = Column(Integer, ForeignKey('import_batch.id'), nullable=False, index=True)
    row_key = Column(String(300), nullable=False)
    entity_type = Column(String(30), nullable=False)
    entity_id = Column(Integer, nullable=True)
    action = Column(String(20), nullable=False)
    source = Column(JSON, nullable=False)
    original_values = Column(JSON, nullable=False)
    normalized_values = Column(JSON, nullable=False)
    decision = Column(JSON, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


class ImportReference(Base):
    __tablename__ = 'import_reference'
    __table_args__ = (UniqueConstraint('source_namespace','entity_type','source_id', name='uq_import_reference'),)
    id = Column(Integer, primary_key=True)
    source_namespace = Column(String(100), nullable=False)
    entity_type = Column(String(30), nullable=False)
    source_id = Column(String(255), nullable=False)
    entity_id = Column(Integer, nullable=False)


class ImportError(Base):
    __tablename__ = 'import_error'
    id = Column(Integer, primary_key=True)
    import_batch_id = Column(Integer, ForeignKey('import_batch.id'), nullable=False, index=True)
    revision = Column(Integer, nullable=False)
    row_key = Column(String(300), nullable=False)
    code = Column(String(80), nullable=False)
    severity = Column(String(20), nullable=False)
    message = Column(Text, nullable=False)
    source = Column(JSON, nullable=False)
    original_values = Column(JSON, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
