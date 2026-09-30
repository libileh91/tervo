"""Technical installation, independently of the future commercial chain."""
import enum
from sqlalchemy import Column, Date, DateTime, Enum, ForeignKey, Integer, Text, func
from sqlalchemy.orm import relationship
from app.models.base import Base


class InstallationStatus(str, enum.Enum):
    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class Installation(Base):
    __tablename__ = "installation"
    id = Column(Integer, primary_key=True, index=True)
    site_id = Column(Integer, ForeignKey("site.id", ondelete="RESTRICT"), nullable=False, index=True)
    scheduled_start = Column(DateTime, nullable=True)
    scheduled_end = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    installation_date = Column(Date, nullable=True)
    commissioning_date = Column(Date, nullable=True)
    status = Column(Enum(InstallationStatus, native_enum=False, create_constraint=True,
                         name="installation_status"), nullable=False,
                    default=InstallationStatus.SCHEDULED, server_default="SCHEDULED", index=True)
    technician_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    site = relationship("Site", back_populates="installations")
    equipment = relationship("Equipment", back_populates="installation", uselist=False,
                             passive_deletes="all")
