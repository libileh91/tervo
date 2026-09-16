"""
Tervo — ChecklistItem model.

Represents a checklist item attached to a job (pre/post intervention).
"""

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.models.base import Base


class ChecklistItem(Base):
    __tablename__ = "checklist_item"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(
        Integer, ForeignKey("job.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category = Column(
        String(20), nullable=False
    )  # 'pre_intervention' | 'post_intervention'
    label = Column(String(255), nullable=False)
    checked = Column(Boolean, default=False, nullable=False)
    note = Column(Text, nullable=True)
    position = Column(Integer, default=0, nullable=False)

    # ── Relationships ───────────────────────────────────────
    job = relationship("Job", back_populates="checklist_items")

    def __repr__(self) -> str:
        return f"<ChecklistItem(id={self.id}, label='{self.label}', checked={self.checked})>"
