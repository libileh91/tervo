"""
Tervo — Client and Site repositories.

Data access layer for the Client and Site models.
"""

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.customers.models import Client, Site


class ClientRepository:
    """Encapsulates all database queries for clients."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def count(self, search: str | None = None) -> int:
        """Count clients, optionally filtered by search."""
        query = select(func.count(Client.id))
        if search:
            query = query.where(
                or_(
                    Client.full_name.ilike(f"%{search}%"),
                    Client.phone.ilike(f"%{search}%"),
                )
            )
        result = await self.db.execute(query)
        return result.scalar_one()

    async def list(
        self, page: int = 1, page_size: int = 25, search: str | None = None
    ) -> list[Client]:
        """Paginated list of clients with optional search."""
        query = select(Client)
        if search:
            query = query.where(
                or_(
                    Client.full_name.ilike(f"%{search}%"),
                    Client.phone.ilike(f"%{search}%"),
                )
            )
        query = (
            query.order_by(Client.full_name.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, client_id: int) -> Client | None:
        """Get a single client by ID."""
        result = await self.db.execute(select(Client).where(Client.id == client_id))
        return result.scalar_one_or_none()

    async def create(self, data: dict) -> Client:
        """Create a new client."""
        client = Client(**data)
        self.db.add(client)
        await self.db.commit()
        await self.db.refresh(client)
        return client

    async def update(self, client: Client, data: dict) -> Client:
        """Update an existing client with partial data."""
        for key, value in data.items():
            if value is not None:
                setattr(client, key, value)
        await self.db.commit()
        await self.db.refresh(client)
        return client

    async def delete(self, client: Client) -> None:
        """Delete a client."""
        await self.db.delete(client)
        await self.db.commit()


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
