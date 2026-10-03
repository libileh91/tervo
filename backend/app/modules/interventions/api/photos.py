"""
Tervo — Photos API router.

Endpoints:
- POST   /interventions/{intervention_id}/photos     → upload a photo (multipart)
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
from app.modules.identity.dependencies import get_current_user
from app.modules.interventions.models.intervention import Intervention
from app.modules.identity.models import User
from app.modules.interventions.services.photo import PhotoService
from app.modules.interventions.models.photo import PhotoUsage
from app.modules.interventions.schemas.intervention import PhotoRef

router = APIRouter(prefix="/interventions", tags=["photos"])


async def _get_intervention_or_404(db: AsyncSession, intervention_id: int, *, for_update: bool = False) -> Intervention:
    query = select(Intervention).where(Intervention.id == intervention_id)
    if for_update:
        query = query.with_for_update().execution_options(populate_existing=True)
    result = await db.execute(query)
    intervention = result.scalar_one_or_none()
    if intervention is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Intervention non trouvée",
        )
    return intervention


def _check_assignation(intervention: Intervention, current_user: User) -> None:
    if intervention.technician_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous n'êtes pas assigné à cette intervention",
        )


@router.get("/{intervention_id}/photos", response_model=list[PhotoRef])
async def list_photos(
    intervention_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_intervention_or_404(db, intervention_id)
    return await PhotoService(db).list_photos(intervention_id)


@router.post("/{intervention_id}/photos", response_model=PhotoRef, status_code=status.HTTP_201_CREATED)
async def upload_photo(
    intervention_id: int,
    file: UploadFile = File(...),
    usage: PhotoUsage = Form(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a classified JPEG/PNG/WebP photo, max 10 MiB."""
    # Verify intervention exists and technician is assigned
    intervention = await _get_intervention_or_404(db, intervention_id, for_update=True)
    _check_assignation(intervention, current_user)

    service = PhotoService(db)
    return await service.upload_photo(intervention_id, file, usage)


@router.delete(
    "/{intervention_id}/photos/{photo_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_photo(
    intervention_id: int,
    photo_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a photo: removes files from disk + DB entry."""
    intervention = await _get_intervention_or_404(db, intervention_id, for_update=True)
    _check_assignation(intervention, current_user)

    service = PhotoService(db)
    await service.delete_photo(intervention_id, photo_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
