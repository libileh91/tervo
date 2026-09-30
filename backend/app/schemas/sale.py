"""Validated sale payloads and responses."""
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field
from app.models.sale import SaleStatus


class SaleLineCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0)
    unit_price: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    description: str | None = Field(default=None, max_length=500)


class SaleCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    client_id: int = Field(gt=0)
    site_id: int = Field(gt=0)
    sale_date: date
    notes: str | None = None
    lines: list[SaleLineCreate] = Field(default_factory=list)


class SaleLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    product_id: int
    quantity: int
    unit_price: Decimal
    description: str | None


class SaleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    client_id: int
    site_id: int
    sale_date: date
    status: SaleStatus
    notes: str | None
    created_at: datetime
    updated_at: datetime
    lines: list[SaleLineResponse]
