"""Atomic installation lifecycle, with conditional writes against competing actions."""
from datetime import datetime, timezone
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError
from app.modules.equipment.models import Equipment, EquipmentStatus
from app.models.installation import Installation, InstallationStatus as Status
from app.modules.sales.models import SaleLine, SaleStatus
from app.repositories.installation import InstallationRepository
from app.schemas.installation import InstallationListResponse, InstallationResponse
from app.modules.equipment.service import EquipmentService


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class InstallationService:
    def __init__(self, db):
        self.db = db
        self.repo = InstallationRepository(db)
        self.references = EquipmentService(db)

    async def _check_sale_line(self, sale_line_id, site_id, exclude_installation_id=None):
        line = await self.db.scalar(select(SaleLine).where(SaleLine.id == sale_line_id)
            .options(selectinload(SaleLine.sale)).with_for_update())
        if line is None:
            raise HTTPException(404, "Ligne de vente non trouvée")
        if line.sale.status != SaleStatus.CONFIRMED:
            raise HTTPException(409, "La vente doit être confirmée")
        if line.sale.site_id != site_id:
            raise HTTPException(422, "Le site doit correspondre à la vente")
        count_query = select(func.count(Installation.id)).where(
            Installation.sale_line_id == sale_line_id,
            Installation.status != Status.CANCELLED,
        )
        if exclude_installation_id is not None:
            count_query = count_query.where(Installation.id != exclude_installation_id)
        linked_count = await self.db.scalar(count_query)
        if linked_count >= line.quantity:
            raise HTTPException(409, "La quantité vendue est déjà entièrement planifiée")
        return line

    async def get_installation(self, installation_id):
        installation = await self.repo.get(installation_id)
        if installation is None:
            raise HTTPException(404, "Installation non trouvée")
        return installation

    async def list_installations(self, page=1, page_size=25, **filters):
        items, total = await self.repo.list(page, page_size, **filters)
        return InstallationListResponse(items=[InstallationResponse.model_validate(i) for i in items],
            total=total, page=page, page_size=page_size,
            pages=max(1, (total + page_size - 1) // page_size))

    async def create_installation(self, body):
        try:
            await self.references.check_site(body.site_id)
            values = body.model_dump()
            if body.sale_line_id is not None:
                line = await self._check_sale_line(body.sale_line_id, body.site_id)
                values["sale_line_id"] = line.id
            installation_id = await self.repo.create(values)
            await self.db.commit()
        except IntegrityError as exc:
            await self.db.rollback()
            raise HTTPException(409, "Le site a changé pendant la création") from exc
        except Exception:
            await self.db.rollback()
            raise
        return await self.get_installation(installation_id)

    async def transition(self, installation_id, action):
        allowed, values = {
            "start": ([Status.SCHEDULED], dict(status=Status.IN_PROGRESS, started_at=utcnow())),
            "cancel": ([Status.SCHEDULED, Status.IN_PROGRESS], dict(status=Status.CANCELLED)),
        }[action]
        try:
            await self.get_installation(installation_id)
            if not await self.repo.transition(installation_id, allowed, values):
                raise HTTPException(409, "Transition impossible depuis ce statut")
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise
        return await self.get_installation(installation_id)

    async def complete(self, installation_id, body):
        try:
            installation = await self.get_installation(installation_id)
            # Claim the transition before touching equipment. This write serializes
            # complete/start/cancel even on databases without SELECT FOR UPDATE.
            if not await self.repo.transition(installation_id, [Status.IN_PROGRESS],
                    dict(status=Status.COMPLETED, completed_at=utcnow(),
                         installation_date=body.installation_date,
                         commissioning_date=body.commissioning_date)):
                raise HTTPException(409, "Seule une installation en cours peut être terminée")
            dates = dict(installed_at=body.installation_date, commissioned_at=body.commissioning_date)
            sale_line = None
            if installation.sale_line_id is not None:
                sale_line = await self._check_sale_line(installation.sale_line_id, installation.site_id,
                                                         exclude_installation_id=installation_id)
            if body.equipment.mode == "create":
                await self.references.check_product(body.equipment.product_id)
                if sale_line is not None and body.equipment.product_id != sale_line.product_id:
                    raise HTTPException(422, "Le produit installé doit correspondre à la ligne vendue")
                await self.repo.create_equipment(dict(site_id=installation.site_id,
                    installation_id=installation_id, **dates,
                    **body.equipment.model_dump(exclude={"mode"})))
            else:
                # Lock against replacement while checking historical dates. The
                # conditional attach below also protects SQLite and stale reads.
                equipment = await self.db.scalar(select(Equipment).where(
                    Equipment.id == body.equipment.equipment_id).with_for_update())
                if equipment is None:
                    raise HTTPException(404, "Équipement non trouvé")
                if sale_line is not None and equipment.product_id != sale_line.product_id:
                    raise HTTPException(422, "L'équipement doit correspondre au produit vendu")
                if equipment.site_id != installation.site_id:
                    raise HTTPException(422, "L'équipement doit appartenir au site de l'installation")
                if (equipment.installation_id is not None or equipment.replaced_by_id is not None
                        or equipment.lifecycle_status != EquipmentStatus.ACTIVE):
                    raise HTTPException(409, "Équipement déjà rattaché ou non actif")
                for field, value in dates.items():
                    previous = getattr(equipment, field)
                    if previous is not None and previous != value:
                        raise HTTPException(409, "Les dates existantes de l'équipement doivent être conservées")
                if not await self.repo.attach_equipment(equipment.id, installation.site_id,
                        dict(installation_id=installation_id, **dates)):
                    raise HTTPException(409, "L'équipement a changé pendant la clôture")
            await self.db.commit()
        except IntegrityError as exc:
            await self.db.rollback()
            raise HTTPException(409, "Conflit de référence ou équipement déjà lié à cette installation") from exc
        except Exception:
            await self.db.rollback()
            raise
        return await self.get_installation(installation_id)
