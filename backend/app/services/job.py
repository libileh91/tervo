"""
Tervo — Job Service.

Business logic for job CRUD and specialized queries.
"""

import uuid
from datetime import date, datetime, time, timedelta

from fastapi import HTTPException, status
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.job import Job, JobStatus
from app.models.user import User
from app.repositories.job import JobRepository
from app.repositories.review import ReviewRepository
from app.schemas.job import (
    DashboardSummaryResponse,
    InProgressJobRef,
    JobCancelResponse,
    JobCompleteRequest,
    JobCompleteResponse,
    JobCreate,
    JobHistoryItem,
    JobHistoryResponse,
    JobListResponse,
    JobResponse,
    JobStartResponse,
    JobUpdate,
    NextJobRef,
    OverdueJobRef,
    TodaySummary,
)
from app.services.checklist import ChecklistService


class JobService:
    """Encapsulates business rules for jobs."""

    def __init__(self, db: AsyncSession):
        self.repo = JobRepository(db)
        self.db = db

    # ── CRUD ───────────────────────────────────────────────

    async def list_jobs(
        self,
        page: int = 1,
        page_size: int = 25,
        status: str | None = None,
        date: str | None = None,
        technician_id: int | None = None,
    ) -> JobListResponse:
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 25
        if page_size > 100:
            page_size = 100

        total = await self.repo.count(status, date, technician_id)
        jobs = await self.repo.list_all(page, page_size, status, date, technician_id)
        pages = (total + page_size - 1) // page_size if total > 0 else 1

        return JobListResponse(
            items=[JobResponse.model_validate(j) for j in jobs],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )

    async def get_job(self, job_id: int) -> JobResponse:
        job = await self._find_or_404(job_id)
        return JobResponse.model_validate(job)

    async def create_job(self, data: JobCreate, current_user: User) -> JobResponse:
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

        job = await self.repo.create(create_data)

        # Seed default checklist items via ChecklistService
        checklist_service = ChecklistService(self.repo.db)
        await checklist_service.create_default_items(job.id)

        # Re-fetch with relationships loaded
        return await self.get_job(job.id)

    async def update_job(self, job_id: int, data: JobUpdate) -> JobResponse:
        job = await self._find_or_404(job_id)
        update_data = {k: v for k, v in data.model_dump().items() if v is not None}
        job = await self.repo.update(job, update_data)
        return JobResponse.model_validate(job)

    async def delete_job(self, job_id: int) -> None:
        job = await self._find_or_404(job_id)
        await self.repo.delete(job)

    # ── Workflow: start ────────────────────────────────────

    async def start_job(self, job_id: int, current_user: User) -> JobStartResponse:
        """Start a job: status → en_cours, started_at = now."""
        job = await self._find_or_404(job_id)

        # 1. Vérifier que le job est planifié
        if job.status != JobStatus.PLANIFIE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le job doit être au statut 'planifié' pour être démarré",
            )

        # 2. Vérifier que le technicien est bien assigné
        if job.technician_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Vous n'êtes pas assigné à ce job",
            )

        # 3. Vérifier qu'il n'a pas déjà un job en cours
        existing = await self.repo.db.execute(
            select(Job.id).where(
                Job.technician_id == current_user.id,
                Job.status == JobStatus.EN_COURS,
                Job.id != job_id,
            ).limit(1)
        )
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Vous avez déjà une intervention en cours. Terminez-la d'abord.",
            )

        # 4. Mettre à jour
        job.status = JobStatus.EN_COURS
        job.started_at = datetime.utcnow()
        await self.repo.db.commit()
        await self.repo.db.refresh(job)

        return JobStartResponse(
            id=job.id,
            status=job.status.value,
            started_at=job.started_at,
        )

    # ── Workflow: cancel ────────────────────────────────────

    async def cancel_job(self, job_id: int, current_user: User) -> JobCancelResponse:
        """Cancel a job: status → annulé."""
        job = await self._find_or_404(job_id)

        # 1. Vérifier que le job est planifié
        if job.status != JobStatus.PLANIFIE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le job doit être au statut 'planifié' pour être annulé",
            )

        # 2. Vérifier que le technicien est bien assigné
        if job.technician_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Vous n'êtes pas assigné à ce job",
            )

        # 3. Mettre à jour
        job.status = JobStatus.ANNULE
        await self.repo.db.commit()
        await self.repo.db.refresh(job)

        return JobCancelResponse(
            id=job.id,
            status=job.status.value,
        )

    # ── Workflow: complete ─────────────────────────────────

    async def complete_job(
        self, job_id: int, current_user: User, body: JobCompleteRequest
    ) -> JobCompleteResponse:
        """Complete a job: status → terminé, completed_at = now."""
        job = await self._find_or_404(job_id)

        # 1. Vérifier que le job est en cours
        if job.status != JobStatus.EN_COURS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le job doit être au statut 'en_cours' pour être terminé",
            )

        # 2. Vérifier que le technicien est bien assigné
        if job.technician_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Vous n'êtes pas assigné à ce job",
            )

        # 3. Valider que la checklist est complete
        checklist_service = ChecklistService(self.repo.db)
        validation = await checklist_service.validate_all_checked(job_id)
        if not validation["is_valid"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=validation["detail"],
            )

        # 4. Photos validation (skip — Phase 2)

        # 5. Mettre à jour
        if body.observations is not None:
            job.observations = body.observations
        job.status = JobStatus.TERMINE
        job.completed_at = datetime.utcnow()
        await self.repo.db.commit()
        await self.repo.db.refresh(job)

        # 6. Créer automatiquement le Review avec share_token
        review_repo = ReviewRepository(self.repo.db)
        share_token = uuid.uuid4().hex
        expires_at = job.completed_at + timedelta(days=30)
        await review_repo.create(
            {
                "job_id": job.id,
                "rating": 5,  # valeur par défaut, sera écrasée par le client
                "share_token": share_token,
                "share_token_expires_at": expires_at.replace(tzinfo=None),
            }
        )

        duration = 0
        if job.started_at and job.completed_at:
            duration = int((job.completed_at - job.started_at).total_seconds() // 60)

        return JobCompleteResponse(
            id=job.id,
            status=job.status.value,
            completed_at=job.completed_at,
            duration_minutes=duration,
            report_url=f"/api/v1/jobs/{job.id}/report/download",
            review_share_token=share_token,
            review_share_url=f"/review/{share_token}",
        )

    # ── Client jobs history (from INT-06) ──────────────────

    async def get_client_jobs(
        self, client_id: int, page: int = 1, page_size: int = 50
    ) -> JobHistoryResponse:
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

        return JobHistoryResponse(
            items=[JobHistoryItem(**row) for row in rows],
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

        # Jobs scheduled for today for this technician
        today_jobs = await self.repo.db.execute(
            select(Job)
            .options(selectinload(Job.client))
            .where(
                Job.scheduled_date == today,
                Job.technician_id == current_user.id,
            )
            .order_by(Job.scheduled_start_time.asc())
        )
        jobs = list(today_jobs.scalars().all())

        # Next planned job (parmi les jobs d'aujourd'hui)
        next_job = None
        for j in jobs:
            if j.status == JobStatus.PLANIFIE:
                next_job = NextJobRef(
                    id=j.id,
                    title=j.title,
                    priority=j.priority.value,
                    client_full_name=j.client.full_name,
                    client_address=j.client.address,
                    scheduled_start_time=j.scheduled_start_time,
                )
                break

        # In-progress job (TOUS les jobs en cours, pas seulement aujourd'hui)
        in_progress_result = await self.repo.db.execute(
            select(Job)
            .options(selectinload(Job.client))
            .where(
                Job.technician_id == current_user.id,
                Job.status == JobStatus.EN_COURS,
                Job.started_at.isnot(None),
            )
            .limit(1)
        )
        in_progress_job_row = in_progress_result.scalar_one_or_none()

        in_progress_job = None
        if in_progress_job_row:
            elapsed = int(
                (
                    datetime.utcnow() - in_progress_job_row.started_at.replace(tzinfo=None)
                ).total_seconds()
                // 60
            )
            in_progress_job = InProgressJobRef(
                id=in_progress_job_row.id,
                title=in_progress_job_row.title,
                started_at=in_progress_job_row.started_at,
                elapsed_minutes=elapsed,
            )

        # Counters
        # Total = jobs d'aujourd'hui + job en cours (même s'il n'est pas d'aujourd'hui)
        jobs_total = len(jobs)
        jobs_in_progress = sum(1 for j in jobs if j.status == JobStatus.EN_COURS)
        if in_progress_job and not any(j.id == in_progress_job.id for j in jobs):
            jobs_in_progress += 1
            jobs_total += 1

        # Terminés = tous les jobs terminés du technicien (toutes dates)
        completed_result = await self.repo.db.execute(
            select(func.count(Job.id)).where(
                Job.technician_id == current_user.id,
                Job.status == JobStatus.TERMINE,
            )
        )
        jobs_completed = completed_result.scalar_one() or 0

        # Overdue jobs (planifiés avec date < today)
        overdue_jobs_raw = await self.repo.list_overdue(current_user.id)
        overdue_jobs = [
            OverdueJobRef(
                id=j.id,
                title=j.title,
                priority=j.priority.value,
                scheduled_date=j.scheduled_date.isoformat(),
                days_overdue=(today - j.scheduled_date).days,
                client_full_name=j.client.full_name,
                client_address=j.client.address,
            )
            for j in overdue_jobs_raw
        ]

        return DashboardSummaryResponse(
            today=TodaySummary(
                date=today.isoformat(),
                jobs_total=jobs_total,
                jobs_in_progress=jobs_in_progress,
                jobs_completed=jobs_completed,
            ),
            next_job=next_job,
            in_progress_job=in_progress_job,
            overdue_jobs=overdue_jobs,
        )

    # ── Internal helpers ───────────────────────────────────

    async def _find_or_404(self, job_id: int):
        job = await self.repo.get_by_id(job_id)
        if job is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job non trouvé",
            )
        return job

    async def _check_client_exists(self, client_id: int) -> None:
        sql = text("SELECT id FROM client WHERE id = :client_id")
        result = await self.db.execute(sql, {"client_id": client_id})
        if result.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Client non trouvé",
            )
