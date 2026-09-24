"""
Tervo — Intervention Repository.

Hybrid: raw SQL for specialized queries + ORM for standard CRUD.
"""

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.intervention import Intervention
from app.models.site import Site


class InterventionRepository:
    """Data access layer for Interventions — ORM + raw SQL."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── ORM-based CRUD ─────────────────────────────────────

    async def count(
        self,
        status: str | None = None,
        date: str | None = None,
        technician_id: int | None = None,
    ) -> int:
        query = select(func.count(Intervention.id))
        if status:
            query = query.where(Intervention.status == status)
        if date:
            query = query.where(Intervention.scheduled_date == date)
        if technician_id is not None:
            query = query.where(Intervention.technician_id == technician_id)
        result = await self.db.execute(query)
        return result.scalar_one()

    async def list_all(
        self,
        page: int = 1,
        page_size: int = 25,
        status: str | None = None,
        date: str | None = None,
        technician_id: int | None = None,
    ) -> list[Intervention]:
        query = select(Intervention).options(
            selectinload(Intervention.site),
            selectinload(Intervention.technician),
            selectinload(Intervention.checklist_items),
            selectinload(Intervention.photos),
            selectinload(Intervention.materials),
        )
        if status:
            query = query.where(Intervention.status == status)
        if date:
            query = query.where(Intervention.scheduled_date == date)
        if technician_id is not None:
            query = query.where(Intervention.technician_id == technician_id)
        query = (
            query.order_by(Intervention.scheduled_date.desc(), Intervention.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, intervention_id: int) -> Intervention | None:
        result = await self.db.execute(
            select(Intervention)
            .options(
                selectinload(Intervention.site).selectinload(Site.client),
                selectinload(Intervention.technician),
                selectinload(Intervention.checklist_items),
                selectinload(Intervention.photos),
                selectinload(Intervention.materials),
            )
            .where(Intervention.id == intervention_id)
        )
        return result.scalar_one_or_none()

    async def create(self, data: dict) -> Intervention:
        intervention = Intervention(**data)
        self.db.add(intervention)
        await self.db.commit()
        await self.db.refresh(intervention)
        return intervention  # type: ignore[arg-type]

    async def update(self, intervention: Intervention, data: dict) -> Intervention:
        for key, value in data.items():
            if value is not None:
                setattr(intervention, key, value)
        await self.db.commit()
        await self.db.refresh(intervention)
        return intervention

    async def delete(self, intervention: Intervention) -> None:
        await self.db.delete(intervention)
        await self.db.commit()

    # ── Dashboard: overdue interventions (INT-55) ───────────

    async def list_overdue(self, technician_id: int) -> list[Intervention]:
        """Return PLANNED interventions with scheduled_date < today for a technician."""
        today = func.current_date()
        query = (
            select(Intervention)
            .options(selectinload(Intervention.site))
            .where(
                Intervention.technician_id == technician_id,
                Intervention.status == "PLANNED",
                Intervention.scheduled_date < today,
            )
            .order_by(Intervention.scheduled_date.asc())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    # ── Raw SQL (from INT-06) ──────────────────────────────

    async def count_by_site(self, site_id: int) -> int:
        sql = text("SELECT COUNT(*) FROM intervention WHERE site_id = :site_id")
        result = await self.db.execute(sql, {"site_id": site_id})
        return result.scalar_one()

    async def list_by_site(
        self, site_id: int, page: int = 1, page_size: int = 50
    ) -> list[dict]:
        offset = (page - 1) * page_size
        sql = text("""
            SELECT i.id, i.title, i.status, i.completed_at, u.full_name AS technician_name
            FROM intervention i
            LEFT JOIN "user" u ON i.technician_id = u.id
            WHERE i.site_id = :site_id
            ORDER BY i.created_at DESC
            LIMIT :limit_val OFFSET :offset_val
        """)
        result = await self.db.execute(
            sql,
            {
                "site_id": site_id,
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
