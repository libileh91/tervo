"""
Tervo — Site Pydantic schemas.

Request/response models for Site CRUD endpoints.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class SiteCreate(BaseModel):
    client_id: int
    name: str = Field(..., min_length=1, max_length=255)
    address: str = Field(..., min_length=1, max_length=500)
    postal_code: str | None = Field(None, max_length=20)
    city: str | None = Field(None, max_length=255)
    country: str | None = Field(None, max_length=100)
    access_notes: str | None = None
    notes: str | None = None


class SiteUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    address: str | None = Field(None, min_length=1, max_length=500)
    postal_code: str | None = Field(None, max_length=20)
    city: str | None = Field(None, max_length=255)
    country: str | None = Field(None, max_length=100)
    access_notes: str | None = None
    notes: str | None = None


class SiteResponse(BaseModel):
    id: int
    client_id: int
    name: str
    address: str
    postal_code: str | None = None
    city: str | None = None
    country: str | None = None
    access_notes: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SiteListResponse(BaseModel):
    items: list[SiteResponse]
    total: int
    page: int
    page_size: int
    pages: int
