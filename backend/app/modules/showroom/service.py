"""Showroom rules: preserve prospect history, do not infer a sale from a status."""

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from app.modules.catalog.models import Product
from app.modules.customers.models import Client
from app.modules.showroom.models import ShowroomVisit, ShowroomVisitProduct
from app.modules.showroom.repository import ShowroomRepository
from app.modules.showroom.schemas import VisitListResponse, VisitResponse


class ShowroomService:
    def __init__(self, db):
        self.db = db
        self.repo = ShowroomRepository(db)

    async def _client_exists(self, client_id):
        if client_id is not None and not await self.db.scalar(select(Client.id).where(Client.id == client_id)):
            raise HTTPException(404, "Client non trouvé")

    async def get(self, visit_id):
        visit = await self.repo.get(visit_id)
        if visit is None:
            raise HTTPException(404, "Visite non trouvée")
        return VisitResponse.model_validate(visit)

    async def list(self, page, page_size, **filters):
        visits, total = await self.repo.list(page, page_size, **filters)
        return VisitListResponse(
            items=[VisitResponse.model_validate(visit) for visit in visits],
            total=total, page=page, page_size=page_size,
            pages=max(1, (total + page_size - 1) // page_size),
        )

    async def create(self, body, user):
        if body.salesperson_id is not None and body.salesperson_id != user.id:
            raise HTTPException(403, "Attribution à un autre commercial non autorisée")
        await self._client_exists(body.client_id)
        values = body.model_dump(exclude={"salesperson_id"})
        values["follow_up_status"] = body.follow_up_status.value
        visit = ShowroomVisit(**values, salesperson_id=user.id)
        try:
            self.db.add(visit)
            await self.db.flush()
            visit_id = visit.id
            await self.db.commit()
        except IntegrityError as exc:
            await self.db.rollback()
            raise HTTPException(409, "Client ou commercial indisponible") from exc
        return await self.get(visit_id)

    async def update(self, visit_id, body):
        visit = await self.repo.get(visit_id)
        if visit is None:
            raise HTTPException(404, "Visite non trouvée")
        changes = body.model_dump(exclude_unset=True)
        if "visited_at" in changes and changes["visited_at"] is None:
            raise HTTPException(422, "Date de visite requise")
        new_client = changes.get("client_id", visit.client_id)
        new_name = changes.get("visitor_name", visit.visitor_name)
        if new_client is None and not new_name:
            raise HTTPException(422, "Nom du visiteur requis pour un prospect")
        await self._client_exists(new_client)
        if "follow_up_status" in changes:
            if changes["follow_up_status"] is None:
                raise HTTPException(422, "Statut de suivi requis")
            changes["follow_up_status"] = changes["follow_up_status"].value
        try:
            for key, value in changes.items():
                setattr(visit, key, value)
            await self.db.commit()
        except IntegrityError as exc:
            await self.db.rollback()
            raise HTTPException(409, "Client indisponible") from exc
        return await self.get(visit_id)

    async def add_product(self, visit_id, product_id):
        if await self.repo.get(visit_id) is None:
            raise HTTPException(404, "Visite non trouvée")
        product = await self.db.get(Product, product_id)
        if product is None:
            raise HTTPException(404, "Produit non trouvé")
        if not product.active:
            raise HTTPException(409, "Produit désactivé")
        try:
            self.db.add(ShowroomVisitProduct(visit_id=visit_id, product_id=product_id))
            await self.db.commit()
        except IntegrityError as exc:
            await self.db.rollback()
            # PK/unique protects against concurrent duplicate presentations.
            if await self.db.scalar(select(ShowroomVisitProduct.visit_id).where(
                ShowroomVisitProduct.visit_id == visit_id,
                ShowroomVisitProduct.product_id == product_id,
            )):
                raise HTTPException(409, "Produit déjà présenté") from exc
            raise HTTPException(409, "Visite ou produit indisponible") from exc
        return await self.get(visit_id)

    async def remove_product(self, visit_id, product_id):
        if await self.repo.get(visit_id) is None:
            raise HTTPException(404, "Visite non trouvée")
        result = await self.db.execute(
            delete(ShowroomVisitProduct).where(
                ShowroomVisitProduct.visit_id == visit_id,
                ShowroomVisitProduct.product_id == product_id,
            )
        )
        if result.rowcount == 0:
            await self.db.rollback()
            raise HTTPException(404, "Produit absent de la visite")
        await self.db.commit()
