"""
Tervo — Material Service.

Business logic for material CRUD.
"""

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.material import MaterialRepository
from app.schemas.intervention import MaterialCreate, MaterialResponse


class MaterialService:
    """Encapsulates business rules for material management."""

    def __init__(self, db: AsyncSession):
        self.repo = MaterialRepository(db)

    async def list_materials(self, intervention_id: int) -> list[MaterialResponse]:
        materials = await self.repo.list_by_intervention(intervention_id)
        return [MaterialResponse.model_validate(m) for m in materials]

    async def create_material(
        self, intervention_id: int, data: MaterialCreate
    ) -> MaterialResponse:
        create_data = data.model_dump()
        create_data["intervention_id"] = intervention_id
        # Auto-assign next position
        existing = await self.repo.list_by_intervention(intervention_id)
        create_data["position"] = len(existing)
        material = await self.repo.create(create_data)
        return MaterialResponse.model_validate(material)

    async def update_material(self, material_id: int, data: dict) -> MaterialResponse:
        material = await self._find_or_404(material_id)
        update_data = {k: v for k, v in data.items() if v is not None}
        material = await self.repo.update(material, update_data)
        return MaterialResponse.model_validate(material)

    async def delete_material(self, material_id: int) -> None:
        material = await self._find_or_404(material_id)
        await self.repo.delete(material)

    async def _find_or_404(self, material_id: int):
        material = await self.repo.get_by_id(material_id)
        if material is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Matériau non trouvé",
            )
        return material
