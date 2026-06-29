"""
ResQ — Materials API router.

Endpoints:
- GET    /jobs/{job_id}/materials              → list
- POST   /jobs/{job_id}/materials              → create
- PUT    /jobs/{job_id}/materials/{id}         → update
- DELETE /jobs/{job_id}/materials/{id}         → delete
"""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.job import Job
from app.models.user import User
from app.schemas.job import MaterialCreate, MaterialResponse, MaterialUpdate
from app.services.material import MaterialService

router = APIRouter(prefix="/jobs", tags=["materials"])


async def _get_job_or_404(db: AsyncSession, job_id: int) -> Job:
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Job non trouvé")
    return job


def _check_assignation(job: Job, current_user: User) -> None:
    if job.technician_id != current_user.id:
        raise HTTPException(status_code=403, detail="Vous n'êtes pas assigné à ce job")


@router.get("/{job_id}/materials", response_model=list[MaterialResponse])
async def list_materials(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all materials for a job, ordered by position."""
    await _get_job_or_404(db, job_id)
    service = MaterialService(db)
    return await service.list_materials(job_id)


@router.post("/{job_id}/materials", response_model=MaterialResponse, status_code=201)
async def create_material(
    job_id: int,
    body: MaterialCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a material to a job."""
    job = await _get_job_or_404(db, job_id)
    _check_assignation(job, current_user)
    service = MaterialService(db)
    return await service.create_material(job_id, body)


@router.put("/{job_id}/materials/{material_id}", response_model=MaterialResponse)
async def update_material(
    job_id: int,
    material_id: int,
    body: MaterialUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a material (name, quantity)."""
    job = await _get_job_or_404(db, job_id)
    _check_assignation(job, current_user)
    service = MaterialService(db)
    return await service.update_material(
        material_id, body.model_dump(exclude_unset=True)
    )


@router.delete("/{job_id}/materials/{material_id}", status_code=204)
async def delete_material(
    job_id: int,
    material_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a material."""
    job = await _get_job_or_404(db, job_id)
    _check_assignation(job, current_user)
    service = MaterialService(db)
    await service.delete_material(material_id)
    return Response(status_code=204)
