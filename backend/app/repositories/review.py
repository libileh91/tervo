"""
ResQ — Review Repository.

Data access layer for Review.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.job import Job
from app.models.review import Review


class ReviewRepository:
    """Encapsulates all database queries for reviews."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_token(self, token: str) -> Review | None:
        """Fetch a review by its share_token, with job + technician eager-loaded."""
        result = await self.db.execute(
            select(Review)
            .options(
                selectinload(Review.job).selectinload(Job.technician),
            )
            .where(Review.share_token == token)
        )
        return result.scalar_one_or_none()

    async def create(self, data: dict) -> Review:
        review = Review(**data)
        self.db.add(review)
        await self.db.commit()
        await self.db.refresh(review)
        return review

    async def update(self, review: Review, data: dict) -> Review:
        for key, value in data.items():
            if value is not None:
                setattr(review, key, value)
        await self.db.commit()
        await self.db.refresh(review)
        return review
