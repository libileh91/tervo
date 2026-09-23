"""
Tervo — Checklist Repository.

Data access layer for ChecklistItem.
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.checklist_item import ChecklistItem


class ChecklistRepository:
    """Encapsulates all database queries for checklist items."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_items(self, intervention_id: int) -> list[ChecklistItem]:
        """Get all items for an intervention, ordered by position."""
        result = await self.db.execute(
            select(ChecklistItem)
            .where(ChecklistItem.intervention_id == intervention_id)
            .order_by(ChecklistItem.position.asc())
        )
        return list(result.scalars().all())

    async def get_item(self, item_id: int) -> ChecklistItem | None:
        """Get a single item by id."""
        result = await self.db.execute(
            select(ChecklistItem).where(ChecklistItem.id == item_id)
        )
        return result.scalar_one_or_none()

    async def update_item(self, item: ChecklistItem, data: dict) -> ChecklistItem:
        """Update checked/note on an item."""
        if "checked" in data:
            item.checked = data["checked"]
        if "note" in data:
            item.note = data["note"]
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def batch_update(self, intervention_id: int, items_data: list[dict]) -> int:
        """Update multiple items. Commit once at the end."""
        count = 0
        for item_data in items_data:
            result = await self.db.execute(
                select(ChecklistItem).where(
                    ChecklistItem.id == item_data["id"],
                    ChecklistItem.intervention_id == intervention_id,
                )
            )
            item = result.scalar_one_or_none()
            if item is None:
                raise ValueError(
                    f"Item {item_data['id']} not found for intervention {intervention_id}"
                )
            if "checked" in item_data:
                item.checked = item_data["checked"]
            if "note" in item_data:
                item.note = item_data["note"]
            count += 1
        await self.db.commit()
        return count

    async def count_unchecked(self, intervention_id: int) -> int:
        """Count unchecked items for an intervention."""
        result = await self.db.execute(
            select(func.count(ChecklistItem.id)).where(
                ChecklistItem.intervention_id == intervention_id,
                ChecklistItem.checked == False,  # ignore [invalid-argument-type]
            )
        )
        return result.scalar_one()

    async def count_unchecked_by_category(self, intervention_id: int) -> dict[str, int]:
        """Count unchecked items grouped by category."""
        result = await self.db.execute(
            select(
                ChecklistItem.category,
                func.count(ChecklistItem.id),
            )
            .where(
                ChecklistItem.intervention_id == intervention_id,
                ChecklistItem.checked == False,
            )
            .group_by(ChecklistItem.category)
        )
        return {row[0]: row[1] for row in result.fetchall()}
