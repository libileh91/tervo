"""Persistence queries for visit history, without loading technical interventions."""

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.modules.showroom.models import ShowroomVisit, ShowroomVisitProduct


class ShowroomRepository:
    def __init__(self, db):
        self.db = db

    async def get(self, visit_id: int) -> ShowroomVisit | None:
        return await self.db.scalar(
            select(ShowroomVisit)
            .options(selectinload(ShowroomVisit.presented_products))
            .where(ShowroomVisit.id == visit_id)
        )

    async def list(self, page: int, page_size: int, *, client_id=None, salesperson_id=None,
                   visited_from=None, visited_to=None, follow_up_status=None, product_id=None):
        stmt = select(ShowroomVisit)
        if client_id is not None:
            stmt = stmt.where(ShowroomVisit.client_id == client_id)
        if salesperson_id is not None:
            stmt = stmt.where(ShowroomVisit.salesperson_id == salesperson_id)
        if visited_from is not None:
            stmt = stmt.where(ShowroomVisit.visited_at >= visited_from)
        if visited_to is not None:
            stmt = stmt.where(ShowroomVisit.visited_at <= visited_to)
        if follow_up_status is not None:
            stmt = stmt.where(ShowroomVisit.follow_up_status == follow_up_status.value)
        if product_id is not None:
            stmt = stmt.where(
                select(ShowroomVisitProduct.visit_id).where(
                    ShowroomVisitProduct.visit_id == ShowroomVisit.id,
                    ShowroomVisitProduct.product_id == product_id,
                ).exists()
            )
        total = await self.db.scalar(select(func.count()).select_from(stmt.subquery()))
        visits = (await self.db.scalars(
            stmt.options(selectinload(ShowroomVisit.presented_products))
            .order_by(ShowroomVisit.visited_at.desc(), ShowroomVisit.id.desc())
            .offset((page - 1) * page_size).limit(page_size)
        )).all()
        return visits, total
