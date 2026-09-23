"""
Tervo — InterventionPhoto model.

Represents a photo attached to an intervention (before/after).
"""

from datetime import datetime
from pathlib import Path

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from app.models.base import Base


class InterventionPhoto(Base):
    __tablename__ = "intervention_photo"

    id = Column(Integer, primary_key=True, index=True)
    intervention_id = Column(
        Integer,
        ForeignKey("intervention.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category = Column(String(20), nullable=False)  # 'avant', 'après'
    file_path = Column(String(500), nullable=False)
    thumbnail_path = Column(String(500), nullable=True)
    taken_at = Column(DateTime, server_default=func.now(), nullable=False)

    # ── Relationships ───────────────────────────────────────
    intervention = relationship("Intervention", back_populates="photos")

    # ── Computed URLs for API responses ────────────────────

    @property
    def file_url(self) -> str:
        return f"/uploads/photos/{Path(self.file_path).name}"

    @property
    def thumbnail_url(self) -> str | None:
        if self.thumbnail_path:
            return f"/uploads/photos/{Path(self.thumbnail_path).name}"
        return None

    def __repr__(self) -> str:
        return f"<InterventionPhoto(id={self.id}, category='{self.category}')>"
