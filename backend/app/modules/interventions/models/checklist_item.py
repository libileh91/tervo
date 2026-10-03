"""
Tervo — ChecklistItem model.

Represents a checklist item attached to an intervention (pre/post).
"""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.base import Base


class ChecklistItem(Base):
    __tablename__ = "checklist_item"

    id = Column(Integer, primary_key=True, index=True)
    intervention_checklist_id = Column(
        Integer,
        ForeignKey("intervention_checklist.id", ondelete="CASCADE", name="fk_checklist_item_snapshot"),
        nullable=False,
        index=True,
    )
    category = Column(
        String(20), nullable=False
    )  # 'pre_intervention' | 'post_intervention'
    label = Column(String(255), nullable=False)
    result = Column(String(100), nullable=True)
    comment = Column(Text, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    position = Column(Integer, default=0, nullable=False)

    # ── Relationships ───────────────────────────────────────
    checklist = relationship("InterventionChecklist", back_populates="items")

    def __repr__(self) -> str:
        return f"<ChecklistItem(id={self.id}, label='{self.label}', result={self.result!r})>"
