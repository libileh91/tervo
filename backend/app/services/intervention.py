"""
Tervo — Intervention Service.

Business logic for intervention CRUD and specialized queries.
"""

import uuid
from datetime import date, datetime, time, timedelta

from fastapi import HTTPException, status
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.intervention import Intervention, InterventionStatus
from app.models.user import User
from app.repositories.intervention import InterventionRepository
from app.repositories.review import ReviewRepository
from app.schemas.intervention import (
    DashboardSummaryResponse,
    InProgressInterventionRef,
    InterventionCancelResponse,
    InterventionCompleteRequest,
    InterventionCompleteResponse,
    InterventionCreate,
    InterventionHistoryItem,
    InterventionHistoryResponse,
    InterventionListResponse,
    InterventionResponse,
    InterventionStartResponse,
    InterventionUpdate,
    NextInterventionRef,
    OverdueInterventionRef,
    TodaySummary,
)
from app.services.checklist import ChecklistService


class InterventionService:
    """Encapsulates business rules for interventions."""

    def __init__(self, db: AsyncSession):
        self.repo = InterventionRepository(db)
        self.db = db

    # ── CRUD ───────────────────────────────────────────────

    async def list_interventions(
        self,
        page: int = 1,
        page_size: int = 25,
        status: str | None = None,
        date: str | None = None,
        technician_id: int | None = None,
    ) -> InterventionListResponse:
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 25
        if page_size > 100:
            page_size = 100

        total = await self.repo.count(status, date, technician_id)
        interventions = await self.repo.list_all(
            page, page_size, status, date, technician_id
        )
        pages = (total + page_size - 1) // page_size if total > 0 else 1

        return InterventionListResponse(
            items=[InterventionResponse.model_validate(i) for i in interventions],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )

    async def get_intervention(self, intervention_id: int) -> InterventionResponse:
        intervention = await self._find_or_404(intervention_id)
        return InterventionResponse.model_validate(intervention)

    async def create_intervention(
        self, data: InterventionCreate, current_user: User
    ) -> InterventionResponse:
        # Validate client exists
        await self._check_client_exists(data.client_id)

        create_data = data.model_dump()

        # Auto-assign the current user as technician
        create_data["technician_id"] = current_user.id

        # Parse time strings if provided
        if create_data.get("scheduled_start_time"):
            create_data["scheduled_start_time"] = time.fromisoformat(
                str(create_data["scheduled_start_time"])
            )
        if create_data.get("scheduled_end_time"):
            create_data["scheduled_end_time"] = time.fromisoformat(
                str(create_data["scheduled_end_time"])
            )

        intervention = await self.repo.create(create_data)

        # Seed default checklist items via ChecklistService
        checklist_service = ChecklistService(self.repo.db)
        await checklist_service.create_default_items(intervention.id)

        # Re-fetch with relationships loaded
        return await self.get_intervention(intervention.id)

    async def update_intervention(
        self, intervention_id: int, data: InterventionUpdate
    ) -> InterventionResponse:
        intervention = await self._find_or_404(intervention_id)
        update_data = {k: v for k, v in data.model_dump().items() if v is not None}
        intervention = await self.repo.update(intervention, update_data)
        return InterventionResponse.model_validate(intervention)

    async def delete_intervention(self, intervention_id: int) -> None:
        intervention = await self._find_or_404(intervention_id)
        await self.repo.delete(intervention)

    # ── Workflow: start ────────────────────────────────────

    async def start_intervention(
        self, intervention_id: int, current_user: User
    ) -> InterventionStartResponse:
        """Start an intervention: status → IN_PROGRESS, started_at = now."""
        intervention = await self._find_or_404(intervention_id)

        # 1. Vérifier que l'intervention est planifiée
        if intervention.status != InterventionStatus.PLANNED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="L'intervention doit être au statut 'PLANNED' pour être démarrée",
            )

        # 2. Vérifier que le technicien est bien assigné
        if intervention.technician_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Vous n'êtes pas assigné à cette intervention",
            )

        # 3. Vérifier qu'il n'a pas déjà une intervention en cours
        existing = await self.repo.db.execute(
            select(Intervention.id).where(
                Intervention.technician_id == current_user.id,
                Intervention.status == InterventionStatus.IN_PROGRESS,
                Intervention.id != intervention_id,
            ).limit(1)
        )
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Vous avez déjà une intervention en cours. Terminez-la d'abord.",
            )

        # 4. Mettre à jour
        intervention.status = InterventionStatus.IN_PROGRESS
        intervention.started_at = datetime.utcnow()
        await self.repo.db.commit()
        await self.repo.db.refresh(intervention)

        return InterventionStartResponse(
            id=intervention.id,
            status=intervention.status.value,
            started_at=intervention.started_at,
        )

    # ── Workflow: cancel ────────────────────────────────────

    async def cancel_intervention(
        self, intervention_id: int, current_user: User
    ) -> InterventionCancelResponse:
        """Cancel an intervention: status → CANCELLED."""
        intervention = await self._find_or_404(intervention_id)

        # 1. Vérifier que l'intervention est planifiée
        if intervention.status != InterventionStatus.PLANNED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="L'intervention doit être au statut 'PLANNED' pour être annulée",
            )

        # 2. Vérifier que le technicien est bien assigné
        if intervention.technician_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Vous n'êtes pas assigné à cette intervention",
            )

        # 3. Mettre à jour
        intervention.status = InterventionStatus.CANCELLED
        await self.repo.db.commit()
        await self.repo.db.refresh(intervention)

        return InterventionCancelResponse(
            id=intervention.id,
            status=intervention.status.value,
        )

    # ── Workflow: complete ─────────────────────────────────

    async def complete_intervention(
        self, intervention_id: int, current_user: User, body: InterventionCompleteRequest
    ) -> InterventionCompleteResponse:
        """Complete an intervention: status → COMPLETED, completed_at = now."""
        intervention = await self._find_or_404(intervention_id)

        # 1. Vérifier que l'intervention est en cours
        if intervention.status != InterventionStatus.IN_PROGRESS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="L'intervention doit être au statut 'IN_PROGRESS' pour être terminée",
            )

        # 2. Vérifier que le technicien est bien assigné
        if intervention.technician_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Vous n'êtes pas assigné à cette intervention",
            )

        # 3. Valider que la checklist est complete
        checklist_service = ChecklistService(self.repo.db)
        validation = await checklist_service.validate_all_checked(intervention_id)
        if not validation["is_valid"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=validation["detail"],
            )

        # 4. Photos validation (skip — Phase 2)

        # 5. Mettre à jour
        if body.observations is not None:
            intervention.observations = body.observations
        intervention.status = InterventionStatus.COMPLETED
        intervention.completed_at = datetime.utcnow()
        await self.repo.db.commit()
        await self.repo.db.refresh(intervention)

        # 6. Créer automatiquement le Review avec share_token
        review_repo = ReviewRepository(self.repo.db)
        share_token = uuid.uuid4().hex
        expires_at = intervention.completed_at + timedelta(days=30)
        await review_repo.create(
            {
                "intervention_id": intervention.id,
                "rating": 5,  # valeur par défaut, sera écrasée par le client
                "share_token": share_token,
                "share_token_expires_at": expires_at.replace(tzinfo=None),
            }
        )

        duration = 0
        if intervention.started_at and intervention.completed_at:
            duration = int(
                (intervention.completed_at - intervention.started_at).total_seconds()
                // 60
            )

        return InterventionCompleteResponse(
            id=intervention.id,
            status=intervention.status.value,
            completed_at=intervention.completed_at,
            duration_minutes=duration,
            report_url=f"/api/v1/interventions/{intervention.id}/report/download",
            review_share_token=share_token,
            review_share_url=f"/review/{share_token}",
        )

    # ── Client interventions history (from INT-06) ──────────

    async def get_client_interventions(
        self, client_id: int, page: int = 1, page_size: int = 50
    ) -> InterventionHistoryResponse:
        await self._check_client_exists(client_id)

        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 50
        if page_size > 100:
            page_size = 100

        total = await self.repo.count_by_client(client_id)
        rows = await self.repo.list_by_client(client_id, page, page_size)
        pages = (total + page_size - 1) // page_size if total > 0 else 1

        return InterventionHistoryResponse(
            items=[InterventionHistoryItem(**row) for row in rows],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )

    # ── Dashboard (INT-12) ──────────────────────────────────

    async def get_dashboard_summary(
        self, current_user: User
    ) -> DashboardSummaryResponse:
        """Get today's dashboard summary for the current technician."""
        today = date.today()

        # Interventions scheduled for today for this technician
        today_interventions = await self.repo.db.execute(
            select(Intervention)
            .options(selectinload(Intervention.client))
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
                    client_full_name=i.client.full_name,
                    client_address=i.client.address,
                    scheduled_start_time=i.scheduled_start_time,
                )
                break

        # In-progress intervention (TOUTES les interventions en cours)
        in_progress_result = await self.repo.db.execute(
            select(Intervention)
            .options(selectinload(Intervention.client))
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
                client_full_name=i.client.full_name,
                client_address=i.client.address,
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

    # ── Internal helpers ───────────────────────────────────

    async def _find_or_404(self, intervention_id: int):
        intervention = await self.repo.get_by_id(intervention_id)
        if intervention is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Intervention non trouvée",
            )
        return intervention

    async def _check_client_exists(self, client_id: int) -> None:
        sql = text("SELECT id FROM client WHERE id = :client_id")
        result = await self.db.execute(sql, {"client_id": client_id})
        if result.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Client non trouvé",
            )
