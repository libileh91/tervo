"""
Tervo — Site repository.

Data access layer for the Site model.
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.site import Site


class SiteRepository:
    """Encapsulates all database queries for sites."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def count(self, client_id: int | None = None) -> int:
        """Count sites, optionally filtered by client."""
        query = select(func.count(Site.id))
        if client_id is not None:
            query = query.where(Site.client_id == client_id)
        result = await self.db.execute(query)
        return result.scalar_one()

    async def list(
        self, page: int = 1, page_size: int = 25, client_id: int | None = None
    ) -> list[Site]:
        """Paginated list of sites with optional client filter."""
        query = select(Site)
        if client_id is not None:
            query = query.where(Site.client_id == client_id)
        query = (
            query.order_by(Site.name.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, site_id: int) -> Site | None:
        """Get a single site by ID."""
        result = await self.db.execute(select(Site).where(Site.id == site_id))
        return result.scalar_one_or_none()

    async def create(self, data: dict) -> Site:
        """Create a new site."""
        site = Site(**data)
        self.db.add(site)
        await self.db.commit()
        await self.db.refresh(site)
        return site

    async def update(self, site: Site, data: dict) -> Site:
        """Update an existing site with partial data."""
        for key, value in data.items():
            if value is not None:
                setattr(site, key, value)
        await self.db.commit()
        await self.db.refresh(site)
        return site

    async def delete(self, site: Site) -> None:
        """Delete a site."""
        await self.db.delete(site)
        await self.db.commit()
