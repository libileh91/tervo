"""
ResQ — Checklist API router.

Endpoints:
- GET    /jobs/{job_id}/checklist         → list items
- POST   /jobs/{job_id}/checklist         → add custom item
- PUT    /jobs/{job_id}/checklist/{item_id} → update single item
- PUT    /jobs/{job_id}/checklist/batch     → batch update
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.repositories.job import JobRepository
from app.schemas.job import (
    BatchUpdateRequest,
    BatchUpdateResponse,
    ChecklistItemRef,
    ChecklistItemUpdate,
)
from app.services.checklist import ChecklistService

router = APIRouter(prefix="/jobs", tags=["checklist"])


async def _get_job_or_404(db: AsyncSession, job_id: int):
    """Return the job ORM object or raise 404."""
    repo = JobRepository(db)
    job = await repo.get_by_id(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job non trouvé",
        )
    return job


def _check_assignation(job, current_user: User) -> None:
    """Raise 403 if the technician is not assigned to the job."""
    if job.technician_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous n'êtes pas assigné à ce job",
        )


@router.get("/{job_id}/checklist", response_model=list[ChecklistItemRef])
async def get_checklist(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all checklist items for a job, ordered by position."""
    await _get_job_or_404(db, job_id)
    service = ChecklistService(db)
    items = await service.get_items(job_id)
    return [ChecklistItemRef.model_validate(item) for item in items]


@router.post("/{job_id}/checklist", response_model=ChecklistItemRef, status_code=201)
async def create_checklist_item(
    job_id: int,
    body: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a custom checklist item."""
    job = await _get_job_or_404(db, job_id)
    _check_assignation(job, current_user)
    service = ChecklistService(db)
    item = await service.add_custom_item(
        job_id, body.get("label", ""), body.get("category", "post_intervention")
    )
    return ChecklistItemRef.model_validate(item)


@router.put("/{job_id}/checklist/batch", response_model=BatchUpdateResponse)
async def batch_update_checklist(
    job_id: int,
    body: BatchUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update multiple checklist items at once."""
    # Verify job exists and technician is assigned
    job = await _get_job_or_404(db, job_id)
    _check_assignation(job, current_user)

    service = ChecklistService(db)
    items_data = [item.model_dump(exclude_unset=True) for item in body.items]
    updated = await service.batch_update(job_id, items_data)
    return BatchUpdateResponse(updated=updated)


@router.put("/{job_id}/checklist/{item_id}", response_model=ChecklistItemRef)
async def update_checklist_item(
    job_id: int,
    item_id: int,
    body: ChecklistItemUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a single checklist item (checked, note)."""
    # Verify job exists and technician is assigned
    job = await _get_job_or_404(db, job_id)
    _check_assignation(job, current_user)

    service = ChecklistService(db)
    data = body.model_dump(exclude_unset=True)
    item = await service.update_item(item_id, data)
    return ChecklistItemRef.model_validate(item)
