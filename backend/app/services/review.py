"""
Tervo — Review Service.

Business logic for public review endpoints.
"""

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.review import ReviewRepository


class ReviewService:
    """Encapsulates business rules for reviews."""

    def __init__(self, db: AsyncSession):
        self.repo = ReviewRepository(db)
        self.db = db

    # ── Internal helpers ───────────────────────────────────

    async def _get_valid_review(self, token: str):
        """Fetch a review by token and validate it exists + is not expired.

        Returns the Review ORM object.
        Raises 404 if token invalid or expired.
        """
        review = await self.repo.get_by_token(token)

        if review is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lien invalide ou expiré",
            )

        # Check expiration
        now = datetime.now(timezone.utc)
        expires = review.share_token_expires_at
        # Naive datetime from DB → make timezone-aware for comparison
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if now > expires:  # type: ignore[operator]
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lien invalide ou expiré",
            )

        return review

    # ── GET (INT-32) ───────────────────────────────────────

    async def get_review_by_token(self, token: str) -> dict:
        """Get review data by share_token. Public (no auth).

        Returns intervention info + technician + already_reviewed status.
        """
        review = await self._get_valid_review(token)

        intervention = review.intervention
        technician = intervention.technician

        return {
            "intervention": {
                "title": intervention.title,
                "completed_at": intervention.completed_at.isoformat()
                if intervention.completed_at
                else None,
            },
            "technician": {
                "full_name": technician.full_name if technician else None,
            },
            "already_reviewed": review.submitted_at is not None,
        }

    # ── POST (INT-33) ──────────────────────────────────────

    async def submit_review(
        self, token: str, rating: int, comment: str | None, reviewer_name: str | None
    ) -> dict:
        """Submit a review (rating + comment). Public (no auth).

        Raises 404 if token invalid/expired.
        Raises 400 if already submitted.
        """
        review = await self._get_valid_review(token)

        # Already submitted?
        if review.submitted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Avis déjà soumis",
            )

        # Update the review
        await self.repo.update(
            review,
            {
                "rating": rating,
                "comment": comment,
                "reviewer_name": reviewer_name,
                "submitted_at": datetime.now(timezone.utc).replace(tzinfo=None),
            },
        )

        return {"message": "Merci pour votre avis !"}
