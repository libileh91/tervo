"""
ResQ — Job Pydantic schemas.

Request/response models for Job CRUD + dashboard.
"""

from __future__ import annotations

from datetime import date, datetime, time

from pydantic import BaseModel, Field

# ── Enums (matching the DB model) ─────────────────────────


class JobStatusEnum(str):
    PLANIFIE = "planifié"
    EN_COURS = "en_cours"
    TERMINE = "terminé"
    ANNULE = "annulé"


class PriorityEnum(str):
    BASSE = "basse"
    NORMALE = "normale"
    HAUTE = "haute"
    URGENTE = "urgente"


# ── CRUD Schemas ──────────────────────────────────────────


class JobCreate(BaseModel):
    client_id: int
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    priority: str = "normale"
    scheduled_date: date
    scheduled_start_time: str | None = None  # HH:MM
    scheduled_end_time: str | None = None


class JobUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    priority: str | None = None
    scheduled_date: date | None = None
    scheduled_start_time: str | None = None
    scheduled_end_time: str | None = None
    observations: str | None = None


class ClientRef(BaseModel):
    id: int
    full_name: str

    model_config = {"from_attributes": True}


class TechnicianRef(BaseModel):
    id: int
    full_name: str | None = None

    model_config = {"from_attributes": True}


class ChecklistItemRef(BaseModel):
    id: int
    category: str
    label: str
    checked: bool
    note: str | None = None
    position: int

    model_config = {"from_attributes": True}


# ── Photo schema (INT-23) ───────────────────────────────────


class PhotoRef(BaseModel):
    id: int
    category: str
    file_url: str
    thumbnail_url: str | None = None
    taken_at: datetime | None = None

    model_config = {"from_attributes": True}


# ── Checklist schemas (INT-18) ───────────────────────────────


class ChecklistItemUpdate(BaseModel):
    """Schema for single item update (checked, note)."""

    checked: bool | None = None
    note: str | None = None


class BatchItemUpdate(ChecklistItemUpdate):
    """Schema for batch item update (with id)."""

    id: int


class BatchUpdateRequest(BaseModel):
    items: list[BatchItemUpdate]


class BatchUpdateResponse(BaseModel):
    updated: int


# ── Material schemas (INT-26) ──────────────────────────────


class MaterialCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    quantity: str | None = Field(None, max_length=50)


class MaterialUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    quantity: str | None = Field(None, max_length=50)


class MaterialResponse(BaseModel):
    id: int
    job_id: int
    name: str
    quantity: str | None = None
    position: int

    model_config = {"from_attributes": True}


# ── Job response (with all relations) ────────────────────────


class JobResponse(BaseModel):
    id: int
    client_id: int
    technician_id: int | None = None
    title: str
    description: str | None = None
    status: str
    priority: str
    scheduled_date: date
    scheduled_start_time: time | None = None
    scheduled_end_time: time | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    observations: str | None = None
    created_at: datetime
    updated_at: datetime
    client: ClientRef | None = None
    technician: TechnicianRef | None = None
    checklist_items: list[ChecklistItemRef] = []
    photos: list[PhotoRef] = []
    materials: list[MaterialResponse] = []

    model_config = {"from_attributes": True}


class JobListResponse(BaseModel):
    items: list[JobResponse]
    total: int
    page: int
    page_size: int
    pages: int


# ── History (from INT-06) ─────────────────────────────────


class JobHistoryItem(BaseModel):
    id: int
    title: str
    status: str
    completed_at: datetime | None = None
    technician_name: str | None = None


class JobHistoryResponse(BaseModel):
    items: list[JobHistoryItem]
    total: int
    page: int
    page_size: int
    pages: int


# ── Workflow schemas (INT-10, INT-11) ────────────────────


class JobStartResponse(BaseModel):
    id: int
    status: str
    started_at: datetime


class JobCompleteRequest(BaseModel):
    observations: str | None = None


class JobCompleteResponse(BaseModel):
    id: int
    status: str
    completed_at: datetime
    duration_minutes: int
    report_url: str | None = None
    review_share_token: str | None = None
    review_share_url: str | None = None


# ── Dashboard (INT-12) ────────────────────────────────────


class TodaySummary(BaseModel):
    date: date | str
    jobs_total: int = 0
    jobs_in_progress: int = 0
    jobs_completed: int = 0


class NextJobRef(BaseModel):
    id: int
    title: str
    priority: str
    client_full_name: str
    client_address: str
    scheduled_start_time: time | None = None


class InProgressJobRef(BaseModel):
    id: int
    title: str
    started_at: datetime
    elapsed_minutes: int = 0


class DashboardSummaryResponse(BaseModel):
    today: TodaySummary
    next_job: NextJobRef | None = None
    in_progress_job: InProgressJobRef | None = None
