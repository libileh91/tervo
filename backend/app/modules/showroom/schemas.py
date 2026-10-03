"""Validated showroom inputs and history responses."""

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.modules.showroom.models import FollowUpStatus


def utc_naive(value: datetime) -> datetime:
    """Persist UTC without a timezone, matching the existing DateTime columns."""
    return value.astimezone(timezone.utc).replace(tzinfo=None) if value.tzinfo else value


class VisitCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_id: int | None = Field(default=None, gt=0)
    visitor_name: str | None = Field(default=None, max_length=255)
    visited_at: datetime
    salesperson_id: int | None = Field(default=None, gt=0)
    follow_up_status: FollowUpStatus = FollowUpStatus.TO_FOLLOW_UP
    notes: str | None = None

    @field_validator("visitor_name")
    @classmethod
    def clean_name(cls, name: str | None) -> str | None:
        return name.strip() or None if name is not None else None

    @field_validator("visited_at")
    @classmethod
    def normalize_visit_date(cls, visited_at: datetime) -> datetime:
        return utc_naive(visited_at)

    @model_validator(mode="after")
    def require_identity(self):
        if self.client_id is None and not self.visitor_name:
            raise ValueError("Nom du visiteur requis pour un prospect")
        return self


class VisitUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_id: int | None = Field(default=None, gt=0)
    visitor_name: str | None = Field(default=None, max_length=255)
    visited_at: datetime | None = None
    follow_up_status: FollowUpStatus | None = None
    notes: str | None = None

    @field_validator("visitor_name")
    @classmethod
    def clean_name(cls, name: str | None) -> str | None:
        return name.strip() or None if name is not None else None

    @field_validator("visited_at")
    @classmethod
    def normalize_visit_date(cls, visited_at: datetime | None) -> datetime | None:
        return utc_naive(visited_at) if visited_at is not None else None


class PresentedProductCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    product_id: int = Field(gt=0)


class VisitResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    client_id: int | None
    visitor_name: str | None
    visited_at: datetime
    salesperson_id: int
    follow_up_status: FollowUpStatus
    notes: str | None
    created_at: datetime
    product_ids: list[int]


class VisitListResponse(BaseModel):
    items: list[VisitResponse]
    total: int
    page: int
    page_size: int
    pages: int
