"""Sale lifecycle and commercial reference validation."""
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.modules.customers.models import Client, Site
from app.modules.catalog.models import Product
from app.modules.sales.models import Sale, SaleLine, SaleStatus



class SaleService:
    def __init__(self, db):
        self.db = db

    async def get(self, sale_id):
        sale = await self.db.scalar(select(Sale).where(Sale.id == sale_id).options(selectinload(Sale.lines)))
        if sale is None:
            raise HTTPException(404, "Vente non trouvée")
        return sale

    async def create(self, data):
        client = await self.db.get(Client, data.client_id)
        if client is None:
            raise HTTPException(404, "Client non trouvé")
        site = await self.db.get(Site, data.site_id)
        if site is None:
            raise HTTPException(404, "Site non trouvé")
        if site.client_id != data.client_id:
            raise HTTPException(422, "Le site ne dépend pas du client indiqué")
        products = {}
        for line in data.lines:
            product = await self.db.get(Product, line.product_id)
            if product is None:
                raise HTTPException(404, "Produit non trouvé")
            products[line.product_id] = product
        sale = Sale(client_id=data.client_id, site_id=data.site_id, sale_date=data.sale_date, notes=data.notes)
        sale.lines = [SaleLine(**line.model_dump()) for line in data.lines]
        self.db.add(sale)
        await self.db.commit()
        return await self.get(sale.id)

    async def transition(self, sale_id, target):
        sale = await self.get(sale_id)
        if sale.status != SaleStatus.DRAFT:
            raise HTTPException(409, "Seule une vente brouillon peut changer de statut")
        if target == SaleStatus.CONFIRMED and not sale.lines:
            raise HTTPException(409, "Une vente confirmée doit contenir au moins une ligne")
        sale.status = target
        await self.db.commit()
        return await self.get(sale_id)
