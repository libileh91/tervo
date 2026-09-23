"""
Tervo — Review API router.

Endpoints:
- GET  /review/{share_token}          → public, no auth (INT-32)
- POST /review/{share_token}/submit   → public, no auth (INT-33)
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.review import (
    ReviewPublicResponse,
    ReviewSubmitRequest,
    ReviewSubmitResponse,
)
from app.services.review import ReviewService

router = APIRouter(prefix="/review", tags=["reviews"])


@router.get(
    "/{share_token}",
    response_model=ReviewPublicResponse,
    summary="Get review info by share token (public)",
)
async def get_review_by_token(
    share_token: str,
    db: AsyncSession = Depends(get_db),
):
    """Aucune authentification requise.

    Retourne les infos de l'intervention (titre, date complétion) + technicien +
    already_reviewed.
    """
    service = ReviewService(db)
    return await service.get_review_by_token(share_token)


@router.post(
    "/{share_token}/submit",
    response_model=ReviewSubmitResponse,
    summary="Submit a review (rating + comment) — public",
)
async def submit_review(
    share_token: str,
    body: ReviewSubmitRequest,
    db: AsyncSession = Depends(get_db),
):
    """Aucune authentification requise.

    Soumet un avis client : note (1-5) + commentaire optionnel + nom optionnel.
    Retourne 400 si déjà soumis.
    """
    service = ReviewService(db)
    return await service.submit_review(
        token=share_token,
        rating=body.rating,
        comment=body.comment,
        reviewer_name=body.reviewer_name,
    )
