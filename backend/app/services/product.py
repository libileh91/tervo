"""Catalogue rules: unique references and preservation of history."""
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from app.models.product import Product
from app.repositories.product import ProductRepository
from app.schemas.product import ProductListResponse, ProductResponse


class ProductService:
    def __init__(self, db):
        self.db = db
        self.repo = ProductRepository(db)

    async def get_product(self, product_id):
        product = await self.repo.get_by_id(product_id)
        if product is None:
            raise HTTPException(404, "Produit non trouvé")
        return product

    async def list_products(self, page=1, page_size=25, **filters):
        products, total = await self.repo.list(page, page_size, **filters)
        return ProductListResponse(items=[ProductResponse.model_validate(p) for p in products],
                                   total=total, page=page, page_size=page_size,
                                   pages=max(1, (total + page_size - 1) // page_size))

    async def _save(self, product):
        try:
            return await self.repo.save(product)
        except IntegrityError:
            await self.db.rollback()
            raise HTTPException(409, "Référence produit déjà utilisée") from None

    async def _check_reference(self, reference, product_id=None):
        existing = await self.repo.get_by_reference(reference)
        if existing is not None and existing.id != product_id:
            raise HTTPException(409, "Référence produit déjà utilisée")

    async def create_product(self, data):
        await self._check_reference(data.reference)
        return await self._save(Product(**data.model_dump()))

    async def update_product(self, product_id, data):
        product = await self.get_product(product_id)
        values = data.model_dump(exclude_unset=True)
        if "reference" in values:
            await self._check_reference(values["reference"], product_id)
        for key, value in values.items():
            setattr(product, key, value)
        return await self._save(product)

    async def deactivate_product(self, product_id):
        product = await self.get_product(product_id)
        product.active = False
        return await self._save(product)
