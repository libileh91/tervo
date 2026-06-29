"""
ResQ — JobPhoto model.

Represents a photo attached to a job (before/after).
"""

from datetime import datetime
from pathlib import Path

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from app.models.base import Base


class JobPhoto(Base):
    __tablename__ = "job_photo"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(
        Integer, ForeignKey("job.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category = Column(String(20), nullable=False)  # 'avant', 'après'
    file_path = Column(String(500), nullable=False)
    thumbnail_path = Column(String(500), nullable=True)
    taken_at = Column(DateTime, server_default=func.now(), nullable=False)

    # ── Relationships ───────────────────────────────────────
    job = relationship("Job", back_populates="photos")

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
        return f"<JobPhoto(id={self.id}, category='{self.category}')>"
