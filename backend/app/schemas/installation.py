"""Explicit create/attach contract; commercial references are not yet supported."""
from datetime import date, datetime, timezone
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from app.models.installation import InstallationStatus
from app.schemas.equipment import EquipmentResponse


class InstallationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    site_id: int = Field(gt=0)
    sale_line_id: int | None = Field(default=None, gt=0)
    scheduled_start: datetime | None = None
    scheduled_end: datetime | None = None
    technician_notes: str | None = None

    @field_validator("scheduled_start", "scheduled_end")
    @classmethod
    def utc_naive(cls, value):
        # Existing DB timestamps are naive UTC; normalize offsets before comparison.
        if value is not None and value.tzinfo is not None:
            return value.astimezone(timezone.utc).replace(tzinfo=None)
        return value

    @model_validator(mode="after")
    def planning_order(self):
        if self.scheduled_end and (not self.scheduled_start or self.scheduled_end < self.scheduled_start):
            raise ValueError("La fin planifiée nécessite un début antérieur ou égal")
        return self


class CreateInstalledEquipment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: Literal["create"]
    product_id: int | None = Field(None, gt=0)
    serial_number: str | None = Field(None, max_length=255)
    notes: str | None = None


class AttachInstalledEquipment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: Literal["attach"]
    equipment_id: int = Field(gt=0)


class InstallationComplete(BaseModel):
    model_config = ConfigDict(extra="forbid")
    installation_date: date
    commissioning_date: date | None = None
    equipment: Annotated[CreateInstalledEquipment | AttachInstalledEquipment, Field(discriminator="mode")]

    @model_validator(mode="after")
    def dates_order(self):
        if self.commissioning_date and self.commissioning_date < self.installation_date:
            raise ValueError("La mise en service doit suivre la pose")
        return self


class InstallationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    site_id: int
    sale_line_id: int | None
    scheduled_start: datetime | None
    scheduled_end: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    installation_date: date | None
    commissioning_date: date | None
    status: InstallationStatus
    technician_notes: str | None
    created_at: datetime
    updated_at: datetime
    equipment: EquipmentResponse | None


class InstallationListResponse(BaseModel):
    items: list[InstallationResponse]
    total: int
    page: int
    page_size: int
    pages: int
