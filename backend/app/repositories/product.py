"""Database access for catalogue products."""
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.product import Product


class ProductRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, product_id: int):
        return await self.db.get(Product, product_id)

    async def get_by_reference(self, reference: str):
        return await self.db.scalar(select(Product).where(Product.reference == reference))

    async def list(self, page, page_size, search=None, brand=None, category=None, active=None):
        filters = []
        if search:
            pattern = "%" + search.replace("/", "//").replace("%", "/%").replace("_", "/_") + "%"
            filters.append(or_(*(column.ilike(pattern, escape="/") for column in
                                (Product.reference, Product.name, Product.brand, Product.model))))
        for column, value in ((Product.brand, brand), (Product.category, category), (Product.active, active)):
            if value is not None:
                filters.append(column == value)
        total = await self.db.scalar(select(func.count(Product.id)).where(*filters))
        rows = await self.db.scalars(select(Product).where(*filters).order_by(Product.name, Product.id)
                                     .offset((page - 1) * page_size).limit(page_size))
        return list(rows.all()), total

    async def save(self, product):
        self.db.add(product)
        await self.db.commit()
        await self.db.refresh(product)
        return product
