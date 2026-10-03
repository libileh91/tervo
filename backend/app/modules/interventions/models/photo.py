"""
Tervo — Photo model.

Represents a classified photo attached to an intervention.
"""

from pathlib import Path

from enum import Enum

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from app.core.base import Base


class PhotoUsage(str, Enum):
    BEFORE = "BEFORE"
    AFTER = "AFTER"
    EQUIPMENT = "EQUIPMENT"
    ANOMALY = "ANOMALY"
    PART = "PART"
    OTHER = "OTHER"


class Photo(Base):
    __tablename__ = "photo"
    __table_args__ = (
        CheckConstraint(
            "usage IN ('BEFORE', 'AFTER', 'EQUIPMENT', 'ANOMALY', 'PART', 'OTHER')",
            name="ck_photo_usage",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    intervention_id = Column(
        Integer,
        ForeignKey("intervention.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    usage = Column(String(20), nullable=False)
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
        return f"<Photo(id={self.id}, usage='{self.usage}')>"
