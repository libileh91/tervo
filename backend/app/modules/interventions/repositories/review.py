"""
Tervo — Review Repository.

Data access layer for Review.
"""

from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.interventions.models.intervention import Intervention
from app.modules.interventions.models.review import Review


class ReviewRepository:
    """Encapsulates all database queries for reviews."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_token(self, token: str) -> Review | None:
        """Fetch a review by its share_token, with intervention + technician eager-loaded."""
        result = await self.db.execute(
            select(Review)
            .options(
                selectinload(Review.intervention).selectinload(Intervention.technician),
            )
            .where(Review.share_token == token)
        )
        return result.scalar_one_or_none()

    async def create(self, data: dict, *, commit: bool = True) -> Review:
        review = Review(**data)
        self.db.add(review)
        if commit:
            await self.db.commit()
        else:
            await self.db.flush()
        await self.db.refresh(review)
        return review

    async def submit_once(
        self, token: str, rating: int, comment: str | None,
        reviewer_name: str | None, now: datetime,
    ) -> bool:
        """A single conditional UPDATE prevents concurrent submissions overwriting each other."""
        result = await self.db.execute(
            update(Review)
            .where(
                Review.share_token == token,
                Review.share_token_expires_at > now,
                Review.submitted_at.is_(None),
            )
            .values(
                rating=rating, comment=comment, reviewer_name=reviewer_name,
                submitted_at=now,
            )
        )
        if result.rowcount != 1:
            await self.db.rollback()
            return False
        await self.db.commit()
        return True
