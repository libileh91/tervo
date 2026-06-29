"""
ResQ — Material Repository.

Data access layer for Material model.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.material import Material


class MaterialRepository:
    """Encapsulates all database queries for materials."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_by_job(self, job_id: int) -> list[Material]:
        result = await self.db.execute(
            select(Material)
            .where(Material.job_id == job_id)
            .order_by(Material.position.asc())
        )
        return list(result.scalars().all())

    async def get_by_id(self, material_id: int) -> Material | None:
        result = await self.db.execute(
            select(Material).where(Material.id == material_id)
        )
        return result.scalar_one_or_none()

    async def create(self, data: dict) -> Material:
        material = Material(**data)
        self.db.add(material)
        await self.db.commit()
        await self.db.refresh(material)
        return material

    async def update(self, material: Material, data: dict) -> Material:
        for key, value in data.items():
            if value is not None:
                setattr(material, key, value)
        await self.db.commit()
        await self.db.refresh(material)
        return material

    async def delete(self, material: Material) -> None:
        await self.db.delete(material)
        await self.db.commit()
