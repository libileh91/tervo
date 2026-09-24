"""Validate physical references and preserve history when replacing equipment."""
from fastapi import HTTPException
from app.models.site import Site
from app.models.product import Product
from app.models.equipment import EquipmentStatus
from app.repositories.equipment import EquipmentRepository
from app.schemas.equipment import EquipmentListResponse, EquipmentResponse


class EquipmentService:
    def __init__(self, db):
        self.db = db
        self.repo = EquipmentRepository(db)

    async def get_equipment(self, equipment_id):
        equipment = await self.repo.get(equipment_id)
        if equipment is None:
            raise HTTPException(404, "Équipement non trouvé")
        return equipment

    async def check_site(self, site_id):
        if await self.db.get(Site, site_id) is None:
            raise HTTPException(404, "Site non trouvé")

    async def check_product(self, product_id):
        if product_id is not None and await self.db.get(Product, product_id) is None:
            raise HTTPException(404, "Produit non trouvé")
        # Historical equipment may reference an inactive catalogue product.

    async def list_equipment(self, page=1, page_size=25, **filters):
        items, total = await self.repo.list(page, page_size, **filters)
        return EquipmentListResponse(items=[EquipmentResponse.model_validate(i) for i in items],
                                     total=total, page=page, page_size=page_size,
                                     pages=max(1, (total + page_size - 1) // page_size))

    async def create_equipment(self, body):
        await self.check_site(body.site_id)
        await self.check_product(body.product_id)
        return await self.repo.create(body.model_dump())

    async def replace_equipment(self, equipment_id, body):
        old = await self.get_equipment(equipment_id)
        if old.replaced_by_id is not None or old.lifecycle_status not in (
            EquipmentStatus.ACTIVE, EquipmentStatus.OUT_OF_SERVICE
        ):
            raise HTTPException(409, "Cet équipement ne peut plus être remplacé")
        await self.check_product(body.new_product_id)
        new = await self.repo.replace(old, dict(product_id=body.new_product_id,
            installed_at=body.installation_date, serial_number=body.serial_number, notes=body.notes))
        if new is None:
            raise HTTPException(409, "Équipement déjà remplacé")
        return new
