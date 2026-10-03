"""
Tervo — Intervention model.

Represents a field intervention (work order) at a client site.
"""

import enum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
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

from app.core.base import Base


class InterventionStatus(str, enum.Enum):
    PLANNED = "PLANNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class InterventionResult(str, enum.Enum):
    RESOLVED = "RESOLVED"
    PARTIALLY_RESOLVED = "PARTIALLY_RESOLVED"
    UNRESOLVED = "UNRESOLVED"
    PART_NEEDED = "PART_NEEDED"
    QUOTE_NEEDED = "QUOTE_NEEDED"
    RESCHEDULE = "RESCHEDULE"


class Priority(str, enum.Enum):
    BASSE = "basse"
    NORMALE = "normale"
    HAUTE = "haute"
    URGENTE = "urgente"


class Intervention(Base):
    __tablename__ = "intervention"
    __table_args__ = (
        CheckConstraint(
            "result IN (" + ", ".join(repr(value.value) for value in InterventionResult) + ")",
            name="ck_intervention_result",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    site_id = Column(
        Integer, ForeignKey("site.id", ondelete="CASCADE"), nullable=False, index=True
    )
    equipment_id = Column(Integer, ForeignKey("equipment.id", ondelete="RESTRICT"), nullable=True, index=True)
    equipment = relationship("Equipment", back_populates="interventions")
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
    result = Column(String(30), nullable=True)
    observations = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # ── Relationships ───────────────────────────────────────
    site = relationship("Site", backref="interventions")
    technician = relationship("User", backref="interventions")
    checklist = relationship(
        "InterventionChecklist", back_populates="intervention", uselist=False,
        cascade="all, delete-orphan",
    )
    checklist_items = relationship(
        "ChecklistItem", secondary="intervention_checklist",
        primaryjoin="Intervention.id == InterventionChecklist.intervention_id",
        secondaryjoin="InterventionChecklist.id == ChecklistItem.intervention_checklist_id",
        viewonly=True, order_by="ChecklistItem.position",
    )
    photos = relationship(
        "Photo",
        back_populates="intervention",
        cascade="all, delete-orphan",
    )
    materials = relationship(
        "MaterialUsage", back_populates="intervention", cascade="all, delete-orphan"
    )
    review = relationship(
        "Review", back_populates="intervention", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<Intervention(id={self.id}, title='{self.title}', "
            f"status='{self.status.value}')>"
        )
