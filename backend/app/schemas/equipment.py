"""Equipment API contracts; replacement creates a distinct physical instance."""
from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.models.equipment import EquipmentStatus


class EquipmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    site_id: int = Field(gt=0)
    product_id: int | None = Field(None, gt=0)
    serial_number: str | None = Field(None, max_length=255)
    installed_at: date | None = None
    commissioned_at: date | None = None
    warranty_start: date | None = None
    warranty_end: date | None = None
    lifecycle_status: EquipmentStatus = EquipmentStatus.ACTIVE
    notes: str | None = None

    @model_validator(mode="after")
    def validate_lifecycle(self):
        if self.lifecycle_status == EquipmentStatus.REPLACED:
            raise ValueError("Utiliser l'action replace pour remplacer un équipement")
        if self.warranty_start and self.warranty_end and self.warranty_end < self.warranty_start:
            raise ValueError("La fin de garantie doit suivre son début")
        return self


class EquipmentReplace(BaseModel):
    model_config = ConfigDict(extra="forbid")
    new_product_id: int | None = Field(None, gt=0)
    installation_date: date | None = None
    serial_number: str | None = Field(None, max_length=255)
    notes: str | None = None


class EquipmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    site_id: int
    product_id: int | None
    installation_id: int | None
    serial_number: str | None
    installed_at: date | None
    commissioned_at: date | None
    warranty_start: date | None
    warranty_end: date | None
    lifecycle_status: EquipmentStatus
    replaced_by_id: int | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class EquipmentListResponse(BaseModel):
    items: list[EquipmentResponse]
    total: int
    page: int
    page_size: int
    pages: int
