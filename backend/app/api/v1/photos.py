"""
Tervo — Photos API router.

Endpoints:
- POST   /jobs/{job_id}/photos     → upload a photo (multipart)
"""

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.job import Job
from app.models.user import User
from app.services.photo import PhotoService

router = APIRouter(prefix="/jobs", tags=["photos"])


async def _get_job_or_404(db: AsyncSession, job_id: int) -> Job:
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job non trouvé",
        )
    return job


def _check_assignation(job: Job, current_user: User) -> None:
    if job.technician_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous n'êtes pas assigné à ce job",
        )


@router.post("/{job_id}/photos", status_code=status.HTTP_201_CREATED)
async def upload_photo(
    job_id: int,
    file: UploadFile = File(...),
    category: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a photo for a job (multipart with JPEG/PNG, max 10 MB)."""
    # Validate category
    if category not in ("avant", "après"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La catégorie doit être 'avant' ou 'après'",
        )

    # Verify job exists and technician is assigned
    job = await _get_job_or_404(db, job_id)
    _check_assignation(job, current_user)

    service = PhotoService(db)
    return await service.upload_photo(job_id, file, category)


@router.delete("/{job_id}/photos/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_photo(
    job_id: int,
    photo_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a photo: removes files from disk + DB entry."""
    # Verify job exists and technician is assigned
    job = await _get_job_or_404(db, job_id)
    _check_assignation(job, current_user)

    service = PhotoService(db)
    await service.delete_photo(photo_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
