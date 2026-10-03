"""
Tervo — Intervention Pydantic schemas.

Request/response models for Intervention CRUD + dashboard.
"""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal

from pydantic import BaseModel, Field, field_serializer, field_validator, model_validator
from app.modules.interventions.models.intervention import InterventionResult
from app.modules.interventions.models.photo import PhotoUsage

# ── Enums (matching the DB model) ─────────────────────────


class InterventionStatusEnum(str):
    PLANNED = "PLANNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class PriorityEnum(str):
    BASSE = "basse"
    NORMALE = "normale"
    HAUTE = "haute"
    URGENTE = "urgente"


# ── CRUD Schemas ──────────────────────────────────────────


class _NoEditableResult(BaseModel):
    @model_validator(mode="before")
    @classmethod
    def refuse_result(cls, data):
        if isinstance(data, dict) and "result" in data:
            raise ValueError("result is only writable through completion")
        return data


class InterventionCreate(_NoEditableResult):
    under_warranty: bool = False
    checklist_template_id: int | None = Field(None, gt=0)
    site_id: int
    equipment_id: int | None = Field(None, gt=0)
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    priority: str = "normale"
    scheduled_date: date
    scheduled_start_time: str | None = None  # HH:MM
    scheduled_end_time: str | None = None


class InterventionUpdate(_NoEditableResult):
    equipment_id: int | None = Field(None, gt=0)
    under_warranty: bool | None = None
    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    priority: str | None = None
    scheduled_date: date | None = None
    scheduled_start_time: str | None = None
    scheduled_end_time: str | None = None
    observations: str | None = None


class SiteRef(BaseModel):
    id: int
    name: str
    address: str

    model_config = {"from_attributes": True}


class TechnicianRef(BaseModel):
    id: int
    full_name: str | None = None

    model_config = {"from_attributes": True}


class ChecklistItemRef(BaseModel):
    id: int
    intervention_checklist_id: int
    category: str
    label: str
    result: str | None = None
    comment: str | None = None
    completed_at: datetime | None = None
    position: int

    model_config = {"from_attributes": True}


# ── Photo schema (INT-23) ───────────────────────────────────


class PhotoRef(BaseModel):
    id: int
    usage: PhotoUsage
    file_url: str
    thumbnail_url: str | None = None
    taken_at: datetime | None = None

    model_config = {"from_attributes": True}


# ── Checklist schemas (INT-18) ───────────────────────────────


class ChecklistItemUpdate(BaseModel):
    """Only completion data is mutable; snapshot structure is immutable."""

    model_config = {"extra": "forbid"}
    result: str | None = Field(None, max_length=100)
    comment: str | None = None

    @field_validator("result")
    @classmethod
    def nonblank_result(cls, value):
        if value is not None and not value.strip():
            raise ValueError("result must be nonblank or null")
        return value


# ── Material schemas (INT-26) ──────────────────────────────


def _bounded_quantity_schema(schema: dict) -> None:
    """Anchor Pydantic's generated Decimal pattern over the entire string."""
    for variant in schema.get("anyOf", []):
        if variant.get("type") == "string" and "pattern" in variant:
            variant["pattern"] = "(?:" + variant["pattern"] + ")$"


class MaterialCreate(BaseModel):
    model_config = {"extra": "forbid"}
    designation: str = Field(..., min_length=1, max_length=255)
    quantity: Decimal = Field(..., gt=0, max_digits=12, decimal_places=3, json_schema_extra=_bounded_quantity_schema)
    unit: str = Field(..., min_length=1, max_length=50)

    @field_validator("designation", "unit")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("must be nonblank")
        return value


class MaterialUpdate(BaseModel):
    model_config = {"extra": "forbid"}
    designation: str = Field(default=None, min_length=1, max_length=255)
    quantity: Decimal = Field(default=None, gt=0, max_digits=12, decimal_places=3, json_schema_extra=_bounded_quantity_schema)
    unit: str = Field(default=None, min_length=1, max_length=50)

    @field_validator("designation", "unit")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("must be nonblank")
        return value


class MaterialResponse(BaseModel):
    id: int
    intervention_id: int
    designation: str
    quantity: Decimal | None = None
    unit: str | None = None
    position: int

    model_config = {"from_attributes": True}

    @field_serializer("quantity", when_used="json")
    def quantity_number(self, value) -> float | None:
        return float(value) if value is not None else None


# ── Intervention response (with all relations) ──────────────


class InterventionResponse(BaseModel):
    id: int
    site_id: int
    equipment_id: int | None = Field(None, gt=0)
    technician_id: int | None = None
    title: str
    description: str | None = None
    status: str
    result: InterventionResult | None = None
    priority: str
    under_warranty: bool = False
    scheduled_date: date
    scheduled_start_time: time | None = None
    scheduled_end_time: time | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    observations: str | None = None
    created_at: datetime
    updated_at: datetime
    site: SiteRef | None = None
    technician: TechnicianRef | None = None
    checklist_items: list[ChecklistItemRef] = []
    photos: list[PhotoRef] = []
    materials: list[MaterialResponse] = []

    model_config = {"from_attributes": True}


class InterventionListResponse(BaseModel):
    items: list[InterventionResponse]
    total: int
    page: int
    page_size: int
    pages: int


# ── History (from INT-06) ─────────────────────────────────


class InterventionHistoryItem(BaseModel):
    id: int
    title: str
    status: str
    result: InterventionResult | None = None
    completed_at: datetime | None = None
    technician_name: str | None = None


class InterventionHistoryResponse(BaseModel):
    items: list[InterventionHistoryItem]
    total: int
    page: int
    page_size: int
    pages: int


# ── Workflow schemas (INT-10, INT-11) ────────────────────


class InterventionStartResponse(BaseModel):
    id: int
    status: str
    started_at: datetime


class InterventionCompleteRequest(BaseModel):
    model_config = {"extra": "forbid"}
    result: InterventionResult
    observations: str | None = None


class InterventionCancelResponse(BaseModel):
    id: int
    status: str


class InterventionCompleteResponse(BaseModel):
    id: int
    status: str
    result: InterventionResult
    completed_at: datetime
    duration_minutes: int
    report_url: str | None = None
    review_share_token: str | None = None
    review_share_url: str | None = None
