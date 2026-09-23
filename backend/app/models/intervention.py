"""
Tervo — Intervention model.

Represents a field intervention (work order) at a client site.
"""

import enum

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    func,
)
from sqlalchemy.orm import relationship

from app.models.base import Base


class InterventionStatus(str, enum.Enum):
    PLANNED = "PLANNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class Priority(str, enum.Enum):
    BASSE = "basse"
    NORMALE = "normale"
    HAUTE = "haute"
    URGENTE = "urgente"


class Intervention(Base):
    __tablename__ = "intervention"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(
        Integer, ForeignKey("client.id", ondelete="CASCADE"), nullable=False, index=True
    )
    technician_id = Column(
        Integer, ForeignKey("user.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(
        Enum(InterventionStatus, values_callable=lambda x: [e.value for e in x]),
        default=InterventionStatus.PLANNED,
        nullable=False,
        index=True,
    )
    priority = Column(
        Enum(Priority, values_callable=lambda x: [e.value for e in x]),
        default=Priority.NORMALE,
        nullable=False,
        index=True,
    )
    under_warranty = Column(Boolean, default=False, nullable=False)
    scheduled_date = Column(Date, nullable=False, index=True)
    scheduled_start_time = Column(Time, nullable=True)
    scheduled_end_time = Column(Time, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    observations = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # ── Relationships ───────────────────────────────────────
    client = relationship("Client", backref="interventions")
    technician = relationship("User", backref="interventions")
    checklist_items = relationship(
        "ChecklistItem", back_populates="intervention", cascade="all, delete-orphan"
    )
    photos = relationship(
        "InterventionPhoto",
        back_populates="intervention",
        cascade="all, delete-orphan",
    )
    materials = relationship(
        "Material", back_populates="intervention", cascade="all, delete-orphan"
    )
    review = relationship(
        "Review", back_populates="intervention", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<Intervention(id={self.id}, title='{self.title}', "
            f"status='{self.status.value}')>"
        )
