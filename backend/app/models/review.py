"""
Tervo — Review model.

Stores client reviews for completed jobs.
Each job can have at most one review (job_id is UNIQUE).
"""

from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from app.models.base import Base


class Review(Base):
    __tablename__ = "review"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(
        Integer,
        ForeignKey("job.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # un seul avis par job
        index=True,
    )
    rating = Column(Integer, nullable=False)  # 1-5
    comment = Column(Text, nullable=True)
    reviewer_name = Column(String(255), nullable=True)
    share_token = Column(String(64), unique=True, nullable=False, index=True)
    share_token_expires_at = Column(DateTime, nullable=False)
    submitted_at = Column(DateTime, nullable=True)  # NULL = pas encore soumis
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # ── Relationships ───────────────────────────────────────
    job = relationship("Job", back_populates="review")

    def __repr__(self) -> str:
        return f"<Review(id={self.id}, job_id={self.job_id}, rating={self.rating})>"
