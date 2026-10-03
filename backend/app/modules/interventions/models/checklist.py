"""Versioned checklist definitions and immutable intervention snapshots."""

from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, ForeignKey, Integer, JSON, String, func
from sqlalchemy.orm import relationship

from app.core.base import Base


class ChecklistTemplate(Base):
    __tablename__ = "checklist_template"
    __table_args__ = (CheckConstraint("version >= 1", name="ck_checklist_template_version"),)

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    intervention_type = Column(String(100), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    active = Column(Boolean, nullable=False, default=True)
    items = Column(JSON, nullable=False)


class InterventionChecklist(Base):
    __tablename__ = "intervention_checklist"
    __table_args__ = (CheckConstraint("template_version >= 1", name="ck_intervention_checklist_template_version"),)

    id = Column(Integer, primary_key=True)
    intervention_id = Column(Integer, ForeignKey("intervention.id", ondelete="CASCADE"), nullable=False, unique=True)
    template_id = Column(Integer, ForeignKey("checklist_template.id", ondelete="RESTRICT"), nullable=True)
    template_name = Column(String(255), nullable=False)
    template_version = Column(Integer, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    intervention = relationship("Intervention", back_populates="checklist")
    items = relationship("ChecklistItem", back_populates="checklist", cascade="all, delete-orphan", order_by="ChecklistItem.position")
