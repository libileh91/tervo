"""
ResQ — Job Repository.

Hybrid: raw SQL for specialized queries + ORM for standard CRUD.
"""

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.job import Job


class JobRepository:
    """Data access layer for Jobs — ORM + raw SQL."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── ORM-based CRUD ─────────────────────────────────────

    async def count(
        self,
        status: str | None = None,
        date: str | None = None,
        technician_id: int | None = None,
    ) -> int:
        query = select(func.count(Job.id))
        if status:
            query = query.where(Job.status == status)
        if date:
            query = query.where(Job.scheduled_date == date)
        if technician_id is not None:
            query = query.where(Job.technician_id == technician_id)
        result = await self.db.execute(query)
        return result.scalar_one()

    async def list_all(
        self,
        page: int = 1,
        page_size: int = 25,
        status: str | None = None,
        date: str | None = None,
        technician_id: int | None = None,
    ) -> list[Job]:
        query = select(Job).options(
            selectinload(Job.client),
            selectinload(Job.technician),
            selectinload(Job.checklist_items),
            selectinload(Job.photos),
            selectinload(Job.materials),
        )
        if status:
            query = query.where(Job.status == status)
        if date:
            query = query.where(Job.scheduled_date == date)
        if technician_id is not None:
            query = query.where(Job.technician_id == technician_id)
        query = (
            query.order_by(Job.scheduled_date.desc(), Job.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, job_id: int) -> Job | None:
        result = await self.db.execute(
            select(Job)
            .options(
                selectinload(Job.client),
                selectinload(Job.technician),
                selectinload(Job.checklist_items),
                selectinload(Job.photos),
                selectinload(Job.materials),
            )
            .where(Job.id == job_id)
        )
        return result.scalar_one_or_none()

    async def create(self, data: dict) -> Job:
        job = Job(**data)
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)
        return job  # type: ignore[arg-type]

    async def update(self, job: Job, data: dict) -> Job:
        for key, value in data.items():
            if value is not None:
                setattr(job, key, value)
        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def delete(self, job: Job) -> None:
        await self.db.delete(job)
        await self.db.commit()

    # ── Raw SQL (from INT-06) ──────────────────────────────

    async def count_by_client(self, client_id: int) -> int:
        sql = text("SELECT COUNT(*) FROM job WHERE client_id = :client_id")
        result = await self.db.execute(sql, {"client_id": client_id})
        return result.scalar_one()

    async def list_by_client(
        self, client_id: int, page: int = 1, page_size: int = 50
    ) -> list[dict]:
        offset = (page - 1) * page_size
        sql = text("""
            SELECT j.id, j.title, j.status, j.completed_at, u.full_name AS technician_name
            FROM job j
            LEFT JOIN "user" u ON j.technician_id = u.id
            WHERE j.client_id = :client_id
            ORDER BY j.created_at DESC
            LIMIT :limit_val OFFSET :offset_val
        """)
        result = await self.db.execute(
            sql,
            {
                "client_id": client_id,
                "limit_val": page_size,
                "offset_val": offset,
            },
        )
        rows = result.fetchall()
        return [
            {
                "id": row.id,
                "title": row.title,
                "status": row.status,
                "completed_at": row.completed_at.isoformat()
                if hasattr(row.completed_at, "isoformat")
                else row.completed_at,
                "technician_name": row.technician_name,
            }
            for row in rows
        ]
