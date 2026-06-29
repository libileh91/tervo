"""
ResQ — Checklist Service.

Business logic for checklist operations.
"""

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.checklist import ChecklistRepository

# ── Default checklist items seeded on job creation ────────

DEFAULT_PRE_ITEMS = [
    ("Vérifier équipement de protection individuelle (EPI)", 1),
    ("Vérifier les accès et sécuriser la zone de travail", 2),
    ("Couper l'alimentation électrique de l'équipement", 3),
]

DEFAULT_POST_ITEMS = [
    ("Nettoyer la zone de travail et remettre en état", 1),
    ("Rétablir l'alimentation et tester le fonctionnement", 2),
]


class ChecklistService:
    """Encapsulates business rules for checklist management."""

    def __init__(self, db: AsyncSession):
        self.repo = ChecklistRepository(db)
        self.db = db

    async def create_default_items(self, job_id: int) -> None:
        """Seed 5 default checklist items (3 pre + 2 post) for a job."""
        from app.models.checklist_item import ChecklistItem

        items = []
        for label, pos in DEFAULT_PRE_ITEMS:
            items.append(
                ChecklistItem(
                    job_id=job_id,
                    category="pre_intervention",
                    label=label,
                    position=pos,
                )
            )
        for label, pos in DEFAULT_POST_ITEMS:
            items.append(
                ChecklistItem(
                    job_id=job_id,
                    category="post_intervention",
                    label=label,
                    position=pos,
                )
            )
        self.db.add_all(items)
        await self.db.commit()

    async def get_items(self, job_id: int) -> list:
        """Get all checklist items for a job, ordered by position.
        If none exist, create default items first."""
        items = await self.repo.get_items(job_id)
        if not items:
            await self.create_default_items(job_id)
            items = await self.repo.get_items(job_id)
        return items

    async def add_custom_item(
        self, job_id: int, label: str, category: str = "post_intervention"
    ) -> "ChecklistItem":
        """Add a custom checklist item to a job."""
        from sqlalchemy import func, select

        from app.models.checklist_item import ChecklistItem

        result = await self.db.execute(
            select(func.max(ChecklistItem.position)).where(
                ChecklistItem.job_id == job_id
            )
        )
        max_pos = result.scalar() or 0
        item = ChecklistItem(
            job_id=job_id,
            category=category,
            label=label or "Item sans nom",
            position=max_pos + 1,
            checked=False,
        )
        self.db.add(item)
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def update_item(self, item_id: int, data: dict):
        """Update checked/note on an item."""
        item = await self.repo.get_item(item_id)
        if item is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item de checklist non trouvé",
            )
        return await self.repo.update_item(item, data)

    async def batch_update(self, job_id: int, items_data: list[dict]) -> int:
        """Update multiple items in a transaction."""
        try:
            return await self.repo.batch_update(job_id, items_data)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )

    async def validate_all_checked(self, job_id: int) -> dict:
        """Validate that all checklist items are checked. Returns detailed errors."""
        unchecked_by_cat = await self.repo.count_unchecked_by_category(job_id)
        total_unchecked = sum(unchecked_by_cat.values())

        if total_unchecked == 0:
            return {"is_valid": True, "errors": []}

        errors = []
        for cat, count in unchecked_by_cat.items():
            label = (
                "pré-intervention" if cat == "pre_intervention" else "post-intervention"
            )
            errors.append(f"{count} item(s) {label} non cochés")

        return {
            "is_valid": False,
            "errors": errors,
            "detail": f"{total_unchecked} items non cochés ({', '.join(e for e in errors)})",
        }
