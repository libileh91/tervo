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
from app.core.deps import get_current_user
from app.models.intervention import Intervention
from app.models.user import User
from app.services.photo import PhotoService

router = APIRouter(prefix="/interventions", tags=["photos"])


async def _get_intervention_or_404(db: AsyncSession, intervention_id: int) -> Intervention:
    result = await db.execute(
        select(Intervention).where(Intervention.id == intervention_id)
    )
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


@router.post("/{intervention_id}/photos", status_code=status.HTTP_201_CREATED)
async def upload_photo(
    intervention_id: int,
    file: UploadFile = File(...),
    category: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a photo for an intervention (multipart with JPEG/PNG, max 10 MB)."""
    # Validate category
    if category not in ("avant", "après"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La catégorie doit être 'avant' ou 'après'",
        )

    # Verify intervention exists and technician is assigned
    intervention = await _get_intervention_or_404(db, intervention_id)
    _check_assignation(intervention, current_user)

    service = PhotoService(db)
    return await service.upload_photo(intervention_id, file, category)


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
    intervention = await _get_intervention_or_404(db, intervention_id)
    _check_assignation(intervention, current_user)

    service = PhotoService(db)
    await service.delete_photo(photo_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
