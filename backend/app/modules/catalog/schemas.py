"""Catalogue request validation and responses."""
from datetime import datetime
from typing import Annotated
from pydantic import BaseModel, ConfigDict, StringConstraints, model_validator

Text255 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
Text100 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class ProductCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reference: Text100
    name: Text255
    brand: Text255
    model: Text255
    category: Text100
    description: str | None = None
    characteristics: dict | None = None
    active: bool = True


class ProductUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reference: Text100 | None = None
    name: Text255 | None = None
    brand: Text255 | None = None
    model: Text255 | None = None
    category: Text100 | None = None
    description: str | None = None
    characteristics: dict | None = None
    active: bool | None = None

    @model_validator(mode="after")
    def reject_null_required_fields(self):
        for field in self.model_fields_set - {"description", "characteristics"}:
            if getattr(self, field) is None:
                raise ValueError(f"{field} ne peut pas être null")
        return self


class ProductResponse(ProductCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    updated_at: datetime


class ProductListResponse(BaseModel):
    items: list[ProductResponse]
    total: int
    page: int
    page_size: int
    pages: int
