"""Existing dashboard response contract."""
from __future__ import annotations

from datetime import date, datetime, time

from pydantic import BaseModel


class TodaySummary(BaseModel):
    date: date | str
    interventions_total: int = 0
    interventions_in_progress: int = 0
    interventions_completed: int = 0


class NextInterventionRef(BaseModel):
    id: int
    title: str
    priority: str
    site_name: str
    site_address: str
    scheduled_start_time: time | None = None


class InProgressInterventionRef(BaseModel):
    id: int
    title: str
    started_at: datetime
    elapsed_minutes: int = 0


class OverdueInterventionRef(BaseModel):
    id: int
    title: str
    priority: str
    scheduled_date: str  # ISO YYYY-MM-DD
    days_overdue: int
    site_name: str
    site_address: str


class DashboardSummaryResponse(BaseModel):
    today: TodaySummary
    next_intervention: NextInterventionRef | None = None
    in_progress_intervention: InProgressInterventionRef | None = None
    overdue_interventions: list[OverdueInterventionRef] = []
