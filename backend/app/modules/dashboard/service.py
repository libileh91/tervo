"""Read-only dashboard projection of the existing field workflow."""
from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.identity.models import User
from app.modules.interventions.models.intervention import Intervention, InterventionStatus
from app.modules.interventions.repositories.intervention import InterventionRepository
from app.modules.dashboard.schemas import (
    DashboardSummaryResponse,
    InProgressInterventionRef,
    NextInterventionRef,
    OverdueInterventionRef,
    TodaySummary,
)


class DashboardService:
    """Aggregate the current technician's dashboard without owning field writes."""

    def __init__(self, db: AsyncSession):
        self.repo = InterventionRepository(db)
        self.db = db

    async def get_dashboard_summary(
        self, current_user: User
    ) -> DashboardSummaryResponse:
        """Get today's dashboard summary for the current technician."""
        today = date.today()

        # Interventions scheduled for today for this technician
        today_interventions = await self.repo.db.execute(
            select(Intervention)
            .options(selectinload(Intervention.site))
            .where(
                Intervention.scheduled_date == today,
                Intervention.technician_id == current_user.id,
            )
            .order_by(Intervention.scheduled_start_time.asc())
        )
        interventions = list(today_interventions.scalars().all())

        # Next planned intervention (parmi les interventions d'aujourd'hui)
        next_intervention = None
        for i in interventions:
            if i.status == InterventionStatus.PLANNED:
                next_intervention = NextInterventionRef(
                    id=i.id,
                    title=i.title,
                    priority=i.priority.value,
                    site_name=i.site.name,
                    site_address=i.site.address,
                    scheduled_start_time=i.scheduled_start_time,
                )
                break

        # In-progress intervention (TOUTES les interventions en cours)
        in_progress_result = await self.repo.db.execute(
            select(Intervention)
            .options(selectinload(Intervention.site))
            .where(
                Intervention.technician_id == current_user.id,
                Intervention.status == InterventionStatus.IN_PROGRESS,
                Intervention.started_at.isnot(None),
            )
            .limit(1)
        )
        in_progress_row = in_progress_result.scalar_one_or_none()

        in_progress_intervention = None
        if in_progress_row:
            elapsed = int(
                (
                    datetime.utcnow()
                    - in_progress_row.started_at.replace(tzinfo=None)
                ).total_seconds()
                // 60
            )
            in_progress_intervention = InProgressInterventionRef(
                id=in_progress_row.id,
                title=in_progress_row.title,
                started_at=in_progress_row.started_at,
                elapsed_minutes=elapsed,
            )

        # Counters
        total = len(interventions)
        in_progress_count = sum(
            1 for i in interventions if i.status == InterventionStatus.IN_PROGRESS
        )
        if in_progress_intervention and not any(
            i.id == in_progress_intervention.id for i in interventions
        ):
            in_progress_count += 1
            total += 1

        # Completed = toutes les interventions terminées du technicien
        completed_result = await self.repo.db.execute(
            select(func.count(Intervention.id)).where(
                Intervention.technician_id == current_user.id,
                Intervention.status == InterventionStatus.COMPLETED,
            )
        )
        completed = completed_result.scalar_one() or 0

        # Overdue interventions (planifiées avec date < today)
        overdue_raw = await self.repo.list_overdue(current_user.id)
        overdue_interventions = [
            OverdueInterventionRef(
                id=i.id,
                title=i.title,
                priority=i.priority.value,
                scheduled_date=i.scheduled_date.isoformat(),
                days_overdue=(today - i.scheduled_date).days,
                site_name=i.site.name,
                site_address=i.site.address,
            )
            for i in overdue_raw
        ]

        return DashboardSummaryResponse(
            today=TodaySummary(
                date=today.isoformat(),
                interventions_total=total,
                interventions_in_progress=in_progress_count,
                interventions_completed=completed,
            ),
            next_intervention=next_intervention,
            in_progress_intervention=in_progress_intervention,
            overdue_interventions=overdue_interventions,
        )
