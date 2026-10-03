"""Metadata only: private PDF bytes never appear in JSON responses."""
from datetime import datetime
from pydantic import BaseModel, StrictBool, field_validator


class ReportVersionResponse(BaseModel):
    id: int
    report_id: int
    version: int
    sha256: str
    size: int
    generated_at: datetime
    generated_by_id: int | None
    transmitted_at: datetime | None
    transmitted_by_id: int | None
    status: str
    storage_key: str
    model_config = {"from_attributes": True}


class ReportResponse(BaseModel):
    id: int
    intervention_id: int
    created_at: datetime
    versions: list[ReportVersionResponse]
    model_config = {"from_attributes": True}


class TransmissionConfirmation(BaseModel):
    model_config = {"extra": "forbid"}
    confirmed: StrictBool

    @field_validator("confirmed")
    @classmethod
    def require_confirmation(cls, value):
        if value is not True:
            raise ValueError("Confirm an external transmission; this endpoint sends no email")
        return value
