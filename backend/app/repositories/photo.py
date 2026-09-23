"""
Tervo — Photo Repository.

Data access layer for InterventionPhoto.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.intervention_photo import InterventionPhoto


class PhotoRepository:
    """Encapsulates all database queries for photos."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: dict) -> InterventionPhoto:
        photo = InterventionPhoto(**data)
        self.db.add(photo)
        await self.db.commit()
        await self.db.refresh(photo)
        return photo

    async def get_by_id(self, photo_id: int) -> InterventionPhoto | None:
        result = await self.db.execute(
            select(InterventionPhoto).where(InterventionPhoto.id == photo_id)
        )
        return result.scalar_one_or_none()

    async def delete(self, photo: InterventionPhoto) -> None:
        await self.db.delete(photo)
        await self.db.commit()
