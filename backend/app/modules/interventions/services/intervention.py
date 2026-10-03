"""
Tervo — Intervention Service.

Business logic for intervention CRUD and specialized queries.
"""

import uuid
from datetime import datetime, time, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.interventions.models.intervention import Intervention, InterventionStatus
from app.modules.customers.models import Site
from app.modules.equipment.models import Equipment
from app.modules.identity.models import User
from app.modules.interventions.repositories.intervention import InterventionRepository
from app.modules.interventions.repositories.review import ReviewRepository
from app.modules.interventions.schemas.intervention import (
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
)
from app.modules.interventions.services.checklist import ChecklistService


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
        # Validate site exists
        await self._check_site_exists(data.site_id)

        await self._check_equipment_site(data.equipment_id, data.site_id)
        create_data = data.model_dump()
        template_id = create_data.pop("checklist_template_id")

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

        try:
            intervention = await self.repo.create(create_data)
            await ChecklistService(self.db).create_snapshot(intervention.id, template_id)
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise

        # Re-fetch with relationships loaded
        return await self.get_intervention(intervention.id)

    async def update_intervention(
        self, intervention_id: int, data: InterventionUpdate
    ) -> InterventionResponse:
        intervention = await self._find_or_404(intervention_id)
        update_data = {k: v for k, v in data.model_dump().items() if v is not None}
        if "equipment_id" in data.model_fields_set:
            await self._check_equipment_site(data.equipment_id, intervention.site_id)
            intervention.equipment_id = data.equipment_id
        intervention = await self.repo.update(intervention, update_data)
        return InterventionResponse.model_validate(intervention)

    async def delete_intervention(self, intervention_id: int) -> None:
        from app.modules.reports.models import Report
        intervention = await self._find_or_404(intervention_id, for_update=True)
        if await self.db.scalar(select(Report.id).where(Report.intervention_id == intervention_id)) is not None:
            raise HTTPException(409, "Un rapport archivé protège l'historique de cette intervention")
        await self.repo.delete(intervention)

    # ── Workflow: start ────────────────────────────────────

    async def start_intervention(
        self, intervention_id: int, current_user: User
    ) -> InterventionStartResponse:
        """Start an intervention: status → IN_PROGRESS, started_at = now."""
        intervention = await self._find_or_404(intervention_id, for_update=True)

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
        intervention = await self._find_or_404(intervention_id, for_update=True)

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
        intervention = await self._find_or_404(intervention_id, for_update=True)

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

        # Outcome and share token are one transaction. Historical outcomes are
        # never inferred from COMPLETED; only this explicit request writes them.
        try:
            if body.observations is not None:
                intervention.observations = body.observations
            intervention.status = InterventionStatus.COMPLETED
            intervention.result = body.result.value
            intervention.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
            share_token = uuid.uuid4().hex
            await ReviewRepository(self.db).create(
                {
                    "intervention_id": intervention.id,
                    "share_token": share_token,
                    "share_token_expires_at": intervention.completed_at + timedelta(days=30),
                },
                commit=False,
            )
            duration = 0
            if intervention.started_at:
                duration = int(
                    (intervention.completed_at - intervention.started_at).total_seconds() // 60
                )
            # Response validation must also succeed before the commit.
            response = InterventionCompleteResponse(
                id=intervention.id,
                status=intervention.status.value,
                result=intervention.result,
                completed_at=intervention.completed_at,
                duration_minutes=duration,
                report_url=f"/api/v1/interventions/{intervention.id}/report/download",
                review_share_token=share_token,
                review_share_url=f"/review/{share_token}",
            )
            await self.db.commit()
            return response
        except Exception:
            await self.db.rollback()
            raise

    # ── Site interventions history (from INT-06) ──────────

    async def get_site_interventions(
        self, site_id: int, page: int = 1, page_size: int = 50
    ) -> InterventionHistoryResponse:
        await self._check_site_exists(site_id)

        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 50
        if page_size > 100:
            page_size = 100

        total = await self.repo.count_by_site(site_id)
        rows = await self.repo.list_by_site(site_id, page, page_size)
        pages = (total + page_size - 1) // page_size if total > 0 else 1

        return InterventionHistoryResponse(
            items=[InterventionHistoryItem(**row) for row in rows],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )

    # ── Internal helpers ───────────────────────────────────

    async def _find_or_404(self, intervention_id: int, *, for_update: bool = False):
        intervention = await self.repo.get_by_id(intervention_id, for_update=for_update)
        if intervention is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Intervention non trouvée",
            )
        return intervention

    async def _check_site_exists(self, site_id: int) -> None:
        site = await self.db.get(Site, site_id)
        if site is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Site non trouvé",
            )


    async def _check_equipment_site(self, equipment_id, site_id):
        if equipment_id is None:
            return
        equipment = await self.db.get(Equipment, equipment_id)
        if equipment is None:
            raise HTTPException(404, "Équipement non trouvé")
        if equipment.site_id != site_id:
            raise HTTPException(422, "L'équipement doit appartenir au site de l'intervention")
