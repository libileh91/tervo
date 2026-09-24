"""Equipment queries and atomic replacement writes."""
from sqlalchemy import func, select, update
from app.models.equipment import Equipment, EquipmentStatus


class EquipmentRepository:
    def __init__(self, db):
        self.db = db

    async def get(self, equipment_id):
        return await self.db.get(Equipment, equipment_id)

    async def list(self, page, page_size, site_id=None, product_id=None, lifecycle_status=None):
        filters = [column == value for column, value in
                   ((Equipment.site_id, site_id), (Equipment.product_id, product_id),
                    (Equipment.lifecycle_status, lifecycle_status)) if value is not None]
        total = await self.db.scalar(select(func.count(Equipment.id)).where(*filters))
        items = await self.db.scalars(select(Equipment).where(*filters).order_by(Equipment.id)
                                     .offset((page - 1) * page_size).limit(page_size))
        return list(items), total

    async def create(self, values):
        equipment = Equipment(**values)
        self.db.add(equipment)
        await self.db.commit()
        await self.db.refresh(equipment)
        return equipment

    async def replace(self, old, values):
        new = Equipment(site_id=old.site_id, **values)
        self.db.add(new)
        try:
            await self.db.flush()
            # Conditional update also protects against concurrent replacements.
            result = await self.db.execute(update(Equipment).where(
                Equipment.id == old.id, Equipment.replaced_by_id.is_(None),
                Equipment.lifecycle_status.in_([EquipmentStatus.ACTIVE, EquipmentStatus.OUT_OF_SERVICE])
            ).values(replaced_by_id=new.id, lifecycle_status=EquipmentStatus.REPLACED))
            if result.rowcount != 1:
                await self.db.rollback()
                return None
            await self.db.commit()
            await self.db.refresh(new)
            return new
        except Exception:
            await self.db.rollback()
            raise
