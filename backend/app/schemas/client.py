"""
Tervo — Client Pydantic schemas.

Request/response models for Client CRUD endpoints.
"""

from datetime import date, datetime

from pydantic import BaseModel, Field


class ClientCreate(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=255)
    phone: str = Field(..., min_length=1, max_length=50)
    email: str | None = Field(None, max_length=255)
    address: str = Field(..., min_length=1, max_length=500)
    postal_code: str | None = Field(None, max_length=20)
    city: str | None = Field(None, max_length=255)
    notes: str | None = None


class ClientUpdate(BaseModel):
    full_name: str | None = Field(None, min_length=1, max_length=255)
    phone: str | None = Field(None, min_length=1, max_length=50)
    email: str | None = Field(None, max_length=255)
    address: str | None = Field(None, min_length=1, max_length=500)
    postal_code: str | None = Field(None, max_length=20)
    city: str | None = Field(None, max_length=255)
    notes: str | None = None


class ClientResponse(BaseModel):
    id: int
    full_name: str
    phone: str
    email: str | None = None
    address: str
    postal_code: str | None = None
    city: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ClientDetailResponse(ClientResponse):
    """Extended response with job statistics."""

    jobs_count: int = 0
    last_job_date: date | None = None


class ClientListResponse(BaseModel):
    items: list[ClientResponse]
    total: int
    page: int
    page_size: int
    pages: int
