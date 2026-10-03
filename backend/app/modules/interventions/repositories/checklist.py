"""Persistence for snapshot completion data."""
from datetime import datetime, timezone
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from app.modules.interventions.models.checklist import InterventionChecklist
from app.modules.interventions.models.checklist_item import ChecklistItem


class ChecklistRepository:
    def __init__(self, db):
        self.db = db

    async def get_snapshot(self, intervention_id):
        return (await self.db.execute(select(InterventionChecklist).where(
            InterventionChecklist.intervention_id == intervention_id
        ).options(selectinload(InterventionChecklist.items)))).scalar_one_or_none()

    async def get_items(self, intervention_id):
        return list((await self.db.execute(select(ChecklistItem).join(InterventionChecklist)
            .where(InterventionChecklist.intervention_id == intervention_id)
            .order_by(ChecklistItem.position, ChecklistItem.id))).scalars())

    async def get_item(self, item_id):
        return await self.db.get(ChecklistItem, item_id)

    async def update_item(self, item, data):
        if "result" in data and data["result"] != item.result:
            item.result = data["result"]
            item.completed_at = datetime.now(timezone.utc).replace(tzinfo=None) if item.result is not None else None
        if "comment" in data:
            item.comment = data["comment"]
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def count_unchecked(self, intervention_id):
        return sum((await self.count_unchecked_by_category(intervention_id)).values())

    async def count_unchecked_by_category(self, intervention_id):
        rows = await self.db.execute(select(ChecklistItem.category, func.count(ChecklistItem.id))
            .join(InterventionChecklist)
            .where(InterventionChecklist.intervention_id == intervention_id, ChecklistItem.result.is_(None))
            .group_by(ChecklistItem.category))
        return dict(rows.all())
