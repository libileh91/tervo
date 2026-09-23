"""
Tervo — Checklist API router.

Endpoints:
- GET    /interventions/{intervention_id}/checklist         → list items
- POST   /interventions/{intervention_id}/checklist         → add custom item
- PUT    /interventions/{intervention_id}/checklist/{item_id} → update single item
- PUT    /interventions/{intervention_id}/checklist/batch     → batch update
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.repositories.intervention import InterventionRepository
from app.schemas.intervention import (
    BatchUpdateRequest,
    BatchUpdateResponse,
    ChecklistItemRef,
    ChecklistItemUpdate,
)
from app.services.checklist import ChecklistService

router = APIRouter(prefix="/interventions", tags=["checklist"])


async def _get_intervention_or_404(db: AsyncSession, intervention_id: int):
    """Return the intervention ORM object or raise 404."""
    repo = InterventionRepository(db)
    intervention = await repo.get_by_id(intervention_id)
    if intervention is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Intervention non trouvée",
        )
    return intervention


def _check_assignation(intervention, current_user: User) -> None:
    """Raise 403 if the technician is not assigned to the intervention."""
    if intervention.technician_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous n'êtes pas assigné à cette intervention",
        )


@router.get("/{intervention_id}/checklist", response_model=list[ChecklistItemRef])
async def get_checklist(
    intervention_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all checklist items for an intervention, ordered by position."""
    await _get_intervention_or_404(db, intervention_id)
    service = ChecklistService(db)
    items = await service.get_items(intervention_id)
    return [ChecklistItemRef.model_validate(item) for item in items]


@router.post("/{intervention_id}/checklist", response_model=ChecklistItemRef, status_code=201)
async def create_checklist_item(
    intervention_id: int,
    body: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a custom checklist item."""
    intervention = await _get_intervention_or_404(db, intervention_id)
    _check_assignation(intervention, current_user)
    service = ChecklistService(db)
    item = await service.add_custom_item(
        intervention_id, body.get("label", ""), body.get("category", "post_intervention")
    )
    return ChecklistItemRef.model_validate(item)


@router.put("/{intervention_id}/checklist/batch", response_model=BatchUpdateResponse)
async def batch_update_checklist(
    intervention_id: int,
    body: BatchUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update multiple checklist items at once."""
    intervention = await _get_intervention_or_404(db, intervention_id)
    _check_assignation(intervention, current_user)

    service = ChecklistService(db)
    items_data = [item.model_dump(exclude_unset=True) for item in body.items]
    updated = await service.batch_update(intervention_id, items_data)
    return BatchUpdateResponse(updated=updated)


@router.put("/{intervention_id}/checklist/{item_id}", response_model=ChecklistItemRef)
async def update_checklist_item(
    intervention_id: int,
    item_id: int,
    body: ChecklistItemUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a single checklist item (checked, note)."""
    intervention = await _get_intervention_or_404(db, intervention_id)
    _check_assignation(intervention, current_user)

    service = ChecklistService(db)
    data = body.model_dump(exclude_unset=True)
    item = await service.update_item(item_id, data)
    return ChecklistItemRef.model_validate(item)
