"""
Tervo — Job model.

Represents an intervention / work order at a client site.
"""

import enum

from sqlalchemy import (
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


class JobStatus(str, enum.Enum):
    PLANIFIE = "planifié"
    EN_COURS = "en_cours"
    TERMINE = "terminé"
    ANNULE = "annulé"


class Priority(str, enum.Enum):
    BASSE = "basse"
    NORMALE = "normale"
    HAUTE = "haute"
    URGENTE = "urgente"


class Job(Base):
    __tablename__ = "job"

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
        Enum(JobStatus, values_callable=lambda x: [e.value for e in x]),
        default=JobStatus.PLANIFIE,
        nullable=False,
        index=True,
    )
    priority = Column(
        Enum(Priority, values_callable=lambda x: [e.value for e in x]),
        default=Priority.NORMALE,
        nullable=False,
        index=True,
    )
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
    client = relationship("Client", backref="jobs")
    technician = relationship("User", backref="jobs")
    # Forward: checklist_items is active (model exists)
    checklist_items = relationship(
        "ChecklistItem", back_populates="job", cascade="all, delete-orphan"
    )
    # Photos and Materials — models now exist (Phase 2)
    photos = relationship(
        "JobPhoto", back_populates="job", cascade="all, delete-orphan"
    )
    materials = relationship(
        "Material", back_populates="job", cascade="all, delete-orphan"
    )
    review = relationship(
        "Review", back_populates="job", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<Job(id={self.id}, title='{self.title}', status='{self.status.value}')>"
        )
