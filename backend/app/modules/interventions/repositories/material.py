"""
Tervo — Material Repository.

Data access layer for MaterialUsage model.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.interventions.models.material_usage import MaterialUsage


class MaterialRepository:
    """Encapsulates all database queries for materials."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_by_intervention(self, intervention_id: int) -> list[MaterialUsage]:
        result = await self.db.execute(
            select(MaterialUsage)
            .where(MaterialUsage.intervention_id == intervention_id)
            .order_by(MaterialUsage.position.asc())
        )
        return list(result.scalars().all())

    async def get_by_id(self, intervention_id: int, material_id: int) -> MaterialUsage | None:
        result = await self.db.execute(
            select(MaterialUsage).where(MaterialUsage.id == material_id, MaterialUsage.intervention_id == intervention_id)
        )
        return result.scalar_one_or_none()

    async def create(self, data: dict) -> MaterialUsage:
        material = MaterialUsage(**data)
        self.db.add(material)
        await self.db.commit()
        await self.db.refresh(material)
        return material

    async def update(self, material: MaterialUsage, data: dict) -> MaterialUsage:
        for key, value in data.items():
            if value is not None:
                setattr(material, key, value)
        await self.db.commit()
        await self.db.refresh(material)
        return material

    async def delete(self, material: MaterialUsage) -> None:
        await self.db.delete(material)
        await self.db.commit()
