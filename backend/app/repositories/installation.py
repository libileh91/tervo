"""Installation persistence; the service owns the transaction, never this repository."""
from sqlalchemy import func, select, update
from sqlalchemy.orm import selectinload
from app.models.installation import Installation
from app.modules.equipment.models import Equipment, EquipmentStatus


class InstallationRepository:
    def __init__(self, db):
        self.db = db

    async def get(self, installation_id):
        return await self.db.scalar(select(Installation).where(Installation.id == installation_id)
            .options(selectinload(Installation.equipment)).execution_options(populate_existing=True))

    async def list(self, page, page_size, site_id=None, status=None):
        filters = [column == value for column, value in
                   ((Installation.site_id, site_id), (Installation.status, status)) if value is not None]
        total = await self.db.scalar(select(func.count(Installation.id)).where(*filters))
        rows = await self.db.scalars(select(Installation).where(*filters)
            .options(selectinload(Installation.equipment)).order_by(Installation.id)
            .offset((page - 1) * page_size).limit(page_size))
        return list(rows), total

    async def create(self, values):
        installation = Installation(**values)
        self.db.add(installation)
        await self.db.flush()
        return installation.id

    async def transition(self, installation_id, allowed, values):
        result = await self.db.execute(update(Installation).where(
            Installation.id == installation_id, Installation.status.in_(allowed)
        ).values(**values).execution_options(synchronize_session=False))
        return result.rowcount == 1

    async def create_equipment(self, values):
        self.db.add(Equipment(**values))
        await self.db.flush()

    async def attach_equipment(self, equipment_id, site_id, values):
        result = await self.db.execute(update(Equipment).where(
            Equipment.id == equipment_id, Equipment.site_id == site_id,
            Equipment.installation_id.is_(None), Equipment.replaced_by_id.is_(None),
            Equipment.lifecycle_status == EquipmentStatus.ACTIVE
        ).values(**values).execution_options(synchronize_session=False))
        return result.rowcount == 1
