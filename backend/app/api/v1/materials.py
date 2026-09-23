"""
Tervo — Materials API router.

Endpoints:
- GET    /interventions/{intervention_id}/materials              → list
- POST   /interventions/{intervention_id}/materials              → create
- PUT    /interventions/{intervention_id}/materials/{id}         → update
- DELETE /interventions/{intervention_id}/materials/{id}         → delete
"""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.intervention import Intervention
from app.models.user import User
from app.schemas.intervention import MaterialCreate, MaterialResponse, MaterialUpdate
from app.services.material import MaterialService

router = APIRouter(prefix="/interventions", tags=["materials"])


async def _get_intervention_or_404(db: AsyncSession, intervention_id: int) -> Intervention:
    result = await db.execute(select(Intervention).where(Intervention.id == intervention_id))
    intervention = result.scalar_one_or_none()
    if intervention is None:
        raise HTTPException(status_code=404, detail="Intervention non trouvée")
    return intervention


def _check_assignation(intervention: Intervention, current_user: User) -> None:
    if intervention.technician_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Vous n'êtes pas assigné à cette intervention"
        )


@router.get("/{intervention_id}/materials", response_model=list[MaterialResponse])
async def list_materials(
    intervention_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all materials for an intervention, ordered by position."""
    await _get_intervention_or_404(db, intervention_id)
    service = MaterialService(db)
    return await service.list_materials(intervention_id)


@router.post("/{intervention_id}/materials", response_model=MaterialResponse, status_code=201)
async def create_material(
    intervention_id: int,
    body: MaterialCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a material to an intervention."""
    intervention = await _get_intervention_or_404(db, intervention_id)
    _check_assignation(intervention, current_user)
    service = MaterialService(db)
    return await service.create_material(intervention_id, body)


@router.put("/{intervention_id}/materials/{material_id}", response_model=MaterialResponse)
async def update_material(
    intervention_id: int,
    material_id: int,
    body: MaterialUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a material (name, quantity)."""
    intervention = await _get_intervention_or_404(db, intervention_id)
    _check_assignation(intervention, current_user)
    service = MaterialService(db)
    return await service.update_material(
        material_id, body.model_dump(exclude_unset=True)
    )


@router.delete("/{intervention_id}/materials/{material_id}", status_code=204)
async def delete_material(
    intervention_id: int,
    material_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a material."""
    intervention = await _get_intervention_or_404(db, intervention_id)
    _check_assignation(intervention, current_user)
    service = MaterialService(db)
    await service.delete_material(material_id)
    return Response(status_code=204)
