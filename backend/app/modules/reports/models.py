"""Private, immutable PDF versions of a logical intervention report."""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, LargeBinary, String, UniqueConstraint, CheckConstraint, func
from sqlalchemy.orm import relationship, deferred
from app.core.base import Base


class Report(Base):
    __tablename__ = "report"
    __table_args__ = (UniqueConstraint("intervention_id", name="uq_report_intervention"),)

    id = Column(Integer, primary_key=True)
    intervention_id = Column(Integer, ForeignKey("intervention.id", ondelete="RESTRICT"), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    intervention = relationship("Intervention", back_populates="report")
    versions = relationship("ReportVersion", back_populates="report", order_by="ReportVersion.version")


class ReportVersion(Base):
    __tablename__ = "report_version"
    __table_args__ = (
        UniqueConstraint("report_id", "version", name="uq_report_version_number"),
        UniqueConstraint("report_id", "request_key", name="uq_report_version_request"),
        CheckConstraint("version >= 1", name="ck_report_version_number"),
        CheckConstraint("size > 0", name="ck_report_version_size"),
    )

    id = Column(Integer, primary_key=True)
    report_id = Column(Integer, ForeignKey("report.id", ondelete="RESTRICT"), nullable=False)
    version = Column(Integer, nullable=False)
    request_key = Column(String(100), nullable=True)
    pdf = deferred(Column(LargeBinary, nullable=False))
    sha256 = Column(String(64), nullable=False)
    size = Column(Integer, nullable=False)
    generated_at = Column(DateTime, nullable=False)
    generated_by_id = Column(Integer, ForeignKey("user.id", ondelete="SET NULL"), nullable=True)
    transmitted_at = Column(DateTime, nullable=True)
    transmitted_by_id = Column(Integer, ForeignKey("user.id", ondelete="SET NULL"), nullable=True)
    report = relationship("Report", back_populates="versions")

    @property
    def status(self):
        return "TRANSMITTED" if self.transmitted_at is not None else "GENERATED"

    @property
    def storage_key(self):
        return f"database:report-version:{self.id}"
