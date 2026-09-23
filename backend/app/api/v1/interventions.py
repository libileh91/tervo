"""
Tervo — Interventions API router.

Endpoints:
- GET    /interventions              → list (paginated, filterable)
- POST   /interventions              → create (with checklist seed)
- GET    /interventions/{id}         → detail
- PUT    /interventions/{id}         → update
- DELETE /interventions/{id}         → delete
"""

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.intervention import (
    InterventionCancelResponse,
    InterventionCompleteRequest,
    InterventionCompleteResponse,
    InterventionCreate,
    InterventionListResponse,
    InterventionResponse,
    InterventionStartResponse,
    InterventionUpdate,
)
from app.services.intervention import InterventionService

router = APIRouter(prefix="/interventions", tags=["interventions"])


@router.get("", response_model=InterventionListResponse)
async def list_interventions(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    status: str | None = Query(None),
    date: str | None = Query(None),
    technician_id: int | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List interventions with pagination and optional filters."""
    service = InterventionService(db)
    return await service.list_interventions(page, page_size, status, date, technician_id)


@router.post("", response_model=InterventionResponse, status_code=status.HTTP_201_CREATED)
async def create_intervention(
    body: InterventionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new intervention (auto-seeds default checklist items)."""
    service = InterventionService(db)
    return await service.create_intervention(body, current_user)


@router.get("/{intervention_id}", response_model=InterventionResponse)
async def get_intervention(
    intervention_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single intervention by ID with full details."""
    service = InterventionService(db)
    return await service.get_intervention(intervention_id)


@router.put("/{intervention_id}", response_model=InterventionResponse)
async def update_intervention(
    intervention_id: int,
    body: InterventionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an intervention (status changes use dedicated endpoints)."""
    service = InterventionService(db)
    return await service.update_intervention(intervention_id, body)


@router.put("/{intervention_id}/start", response_model=InterventionStartResponse)
async def start_intervention(
    intervention_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Start an intervention: status → IN_PROGRESS, started_at = now."""
    service = InterventionService(db)
    return await service.start_intervention(intervention_id, current_user)


@router.put("/{intervention_id}/cancel", response_model=InterventionCancelResponse)
async def cancel_intervention(
    intervention_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel an intervention: status → CANCELLED (only if currently PLANNED)."""
    service = InterventionService(db)
    return await service.cancel_intervention(intervention_id, current_user)


@router.put("/{intervention_id}/complete", response_model=InterventionCompleteResponse)
async def complete_intervention(
    intervention_id: int,
    body: InterventionCompleteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Complete an intervention: status → COMPLETED, completed_at = now."""
    service = InterventionService(db)
    return await service.complete_intervention(intervention_id, current_user, body)


@router.delete("/{intervention_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_intervention(
    intervention_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete an intervention."""
    service = InterventionService(db)
    await service.delete_intervention(intervention_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
