"""
Tervo — Client and Site services.

Business logic layer for client and site operations.
"""

from datetime import date

from fastapi import HTTPException, status
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.interventions.models.intervention import Intervention
from app.modules.equipment.models import Equipment
from app.modules.installations.models import Installation
from app.modules.customers.models import Client, Site
from app.modules.customers.repository import ClientRepository, SiteRepository
from app.modules.customers.schemas import (
    ClientCreate,
    ClientDetailResponse,
    ClientListResponse,
    ClientResponse,
    ClientUpdate,
    SiteCreate,
    SiteListResponse,
    SiteResponse,
    SiteUpdate,
)


class ClientService:
    """Encapsulates business rules for client management."""

    def __init__(self, db: AsyncSession):
        self.repo = ClientRepository(db)

    async def list_clients(
        self, page: int = 1, page_size: int = 25, search: str | None = None
    ) -> ClientListResponse:
        """Get a paginated list of clients."""
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 25
        if page_size > 100:
            page_size = 100

        total = await self.repo.count(search)
        clients = await self.repo.list(page, page_size, search)
        pages = (total + page_size - 1) // page_size if total > 0 else 1

        return ClientListResponse(
            items=[ClientResponse.model_validate(c) for c in clients],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )

    async def get_client(self, client_id: int) -> ClientDetailResponse:
        """Get a single client by ID with intervention stats (real DB queries)."""
        client = await self._find_or_404(client_id)

        # Query real intervention stats via ORM (through the site chain)
        stats_query = (
            select(
                func.count(Intervention.id),
                func.max(Intervention.created_at),
            )
            .join(Site, Intervention.site_id == Site.id)
            .where(Site.client_id == client_id)
        )
        result = await self.repo.db.execute(stats_query)
        row = result.fetchone()
        interventions_count = row[0] if row else 0
        last_intervention_date = row[1].date() if row and row[1] else None

        return ClientDetailResponse(
            **{  # type: ignore
                **client.__dict__,
                "interventions_count": interventions_count,
                "last_intervention_date": last_intervention_date,
            }
        )

    async def create_client(self, data: ClientCreate) -> ClientResponse:
        """Create a new client."""
        client = await self.repo.create(data.model_dump())
        return ClientResponse.model_validate(client)

    async def update_client(self, client_id: int, data: ClientUpdate) -> ClientResponse:
        """Update an existing client."""
        client = await self._find_or_404(client_id)
        # Filter out None values (partial update)
        update_data = {k: v for k, v in data.model_dump().items() if v is not None}
        client = await self.repo.update(client, update_data)
        return ClientResponse.model_validate(client)

    async def delete_client(self, client_id: int) -> None:
        """Delete a client."""
        client = await self._find_or_404(client_id)
        if await self.repo.db.scalar(select(Equipment.id).join(Site).where(Site.client_id == client_id).limit(1)):
            raise HTTPException(409, "Ce client possède des équipements : conserver leur historique")
        if await self.repo.db.scalar(select(Installation.id).join(Site).where(Site.client_id == client_id).limit(1)):
            raise HTTPException(409, "Ce client possède des installations : conserver leur historique")
        await self.repo.delete(client)

    async def _find_or_404(self, client_id: int):
        """Find a client by ID or raise 404."""
        client = await self.repo.get_by_id(client_id)
        if client is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Client non trouvé",
            )
        return client


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
        if await self.db.scalar(select(Installation.id).where(Installation.site_id == site_id).limit(1)):
            raise HTTPException(409, "Ce site possède des installations : conserver leur historique")
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
