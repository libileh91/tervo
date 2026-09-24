"""
Tervo — Site service.

Business logic layer for site operations.
"""

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.equipment import Equipment

from app.models.client import Client
from app.repositories.site import SiteRepository
from app.schemas.site import (
    SiteCreate,
    SiteListResponse,
    SiteResponse,
    SiteUpdate,
)


class SiteService:
    """Encapsulates business rules for site management."""

    def __init__(self, db: AsyncSession):
        self.repo = SiteRepository(db)
        self.db = db

    async def list_sites(
        self,
        page: int = 1,
        page_size: int = 25,
        client_id: int | None = None,
    ) -> SiteListResponse:
        """Get a paginated list of sites, optionally filtered by client."""
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 25
        if page_size > 100:
            page_size = 100

        total = await self.repo.count(client_id)
        sites = await self.repo.list(page, page_size, client_id)
        pages = (total + page_size - 1) // page_size if total > 0 else 1

        return SiteListResponse(
            items=[SiteResponse.model_validate(s) for s in sites],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )

    async def list_sites_for_client(
        self, client_id: int, page: int = 1, page_size: int = 25
    ) -> SiteListResponse:
        """List sites for a client (404 if the client doesn't exist)."""
        await self._check_client_exists(client_id)
        return await self.list_sites(page, page_size, client_id=client_id)

    async def get_site(self, site_id: int) -> SiteResponse:
        """Get a single site by ID."""
        site = await self._find_or_404(site_id)
        return SiteResponse.model_validate(site)

    async def create_site(self, data: SiteCreate) -> SiteResponse:
        """Create a new site (validates the client exists)."""
        await self._check_client_exists(data.client_id)
        site = await self.repo.create(data.model_dump())
        return SiteResponse.model_validate(site)

    async def update_site(self, site_id: int, data: SiteUpdate) -> SiteResponse:
        """Update an existing site (partial update)."""
        site = await self._find_or_404(site_id)
        update_data = {k: v for k, v in data.model_dump().items() if v is not None}
        site = await self.repo.update(site, update_data)
        return SiteResponse.model_validate(site)

    async def delete_site(self, site_id: int) -> None:
        """Delete a site."""
        site = await self._find_or_404(site_id)
        if await self.db.scalar(select(Equipment.id).where(Equipment.site_id == site_id).limit(1)):
            raise HTTPException(409, "Ce site possède des équipements : conserver leur historique")
        await self.repo.delete(site)

    async def _find_or_404(self, site_id: int):
        """Find a site by ID or raise 404."""
        site = await self.repo.get_by_id(site_id)
        if site is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Site non trouvé",
            )
        return site

    async def _check_client_exists(self, client_id: int) -> None:
        """Raise 404 if the client doesn't exist."""
        client = await self.db.get(Client, client_id)
        if client is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Client non trouvé",
            )
