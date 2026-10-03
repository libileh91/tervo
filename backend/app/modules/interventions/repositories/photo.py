"""Persistence for intervention photos."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.interventions.models.photo import Photo


class PhotoRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_by_intervention(self, intervention_id: int) -> list[Photo]:
        result = await self.db.execute(
            select(Photo).where(Photo.intervention_id == intervention_id).order_by(Photo.id)
        )
        return list(result.scalars().all())

    async def create(self, data: dict) -> Photo:
        photo = Photo(**data)
        self.db.add(photo)
        await self.db.flush()
        await self.db.refresh(photo)
        return photo

    async def get_by_id(self, intervention_id: int, photo_id: int) -> Photo | None:
        result = await self.db.execute(
            select(Photo).where(Photo.id == photo_id, Photo.intervention_id == intervention_id)
        )
        return result.scalar_one_or_none()

    async def delete(self, photo: Photo) -> None:
        await self.db.delete(photo)
        await self.db.commit()
