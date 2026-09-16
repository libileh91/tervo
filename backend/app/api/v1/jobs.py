"""
Tervo — Jobs API router.

Endpoints:
- GET    /jobs              → list (paginated, filterable)
- POST   /jobs              → create (with checklist seed)
- GET    /jobs/{id}         → detail
- PUT    /jobs/{id}         → update
- DELETE /jobs/{id}         → delete
"""

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.job import (
    JobCancelResponse,
    JobCompleteRequest,
    JobCompleteResponse,
    JobCreate,
    JobListResponse,
    JobResponse,
    JobStartResponse,
    JobUpdate,
)
from app.services.job import JobService

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=JobListResponse)
async def list_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    status: str | None = Query(None),
    date: str | None = Query(None),
    technician_id: int | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List jobs with pagination and optional filters."""
    service = JobService(db)
    return await service.list_jobs(page, page_size, status, date, technician_id)


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    body: JobCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new job (auto-seeds default checklist items)."""
    service = JobService(db)
    return await service.create_job(body, current_user)


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single job by ID with full details."""
    service = JobService(db)
    return await service.get_job(job_id)


@router.put("/{job_id}", response_model=JobResponse)
async def update_job(
    job_id: int,
    body: JobUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a job (status changes use dedicated endpoints)."""
    service = JobService(db)
    return await service.update_job(job_id, body)


@router.put("/{job_id}/start", response_model=JobStartResponse)
async def start_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Start a job: status → en_cours, started_at = now."""
    service = JobService(db)
    return await service.start_job(job_id, current_user)


@router.put("/{job_id}/cancel", response_model=JobCancelResponse)
async def cancel_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a job: status → annulé (only if currently 'planifié')."""
    service = JobService(db)
    return await service.cancel_job(job_id, current_user)


@router.put("/{job_id}/complete", response_model=JobCompleteResponse)
async def complete_job(
    job_id: int,
    body: JobCompleteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Complete a job: status → terminé, completed_at = now."""
    service = JobService(db)
    return await service.complete_job(job_id, current_user, body)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a job."""
    service = JobService(db)
    await service.delete_job(job_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
