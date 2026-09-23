"""
Tervo — Review Pydantic schemas.

Request/response models for public review endpoints.
"""

from pydantic import BaseModel, Field

# ── Public schemas (INT-32) ────────────────────────────────


class ReviewInterventionInfo(BaseModel):
    """Intervention info exposed publicly via review link."""

    title: str
    completed_at: str | None = None


class ReviewTechnicianInfo(BaseModel):
    """Technician info exposed publicly via review link."""

    full_name: str | None = None


class ReviewPublicResponse(BaseModel):
    """Response for GET /review/{share_token} (public, no auth)."""

    intervention: ReviewInterventionInfo
    technician: ReviewTechnicianInfo
    already_reviewed: bool


# ── Submit schemas (INT-33) ────────────────────────────────


class ReviewSubmitRequest(BaseModel):
    """Body for POST /review/{share_token}/submit."""

    rating: int = Field(..., ge=1, le=5, description="Note de 1 à 5")
    comment: str | None = Field(
        None, max_length=2000, description="Commentaire optionnel"
    )
    reviewer_name: str | None = Field(
        None, max_length=255, description="Nom du client (optionnel)"
    )


class ReviewSubmitResponse(BaseModel):
    """Response after successful review submission."""

    message: str = "Merci pour votre avis !"
