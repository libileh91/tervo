"""INT-111: add a small, synthetic backup fixture through existing services.

Run inside the backend container with --confirm-db <actual database name>.
No seed, schema creation, deletion, user creation, or modification of existing
business records. Each service commits normally; reruns reuse marked records.
"""

import argparse
import asyncio
import hashlib
import io
from datetime import date
from pathlib import Path

from fastapi import UploadFile
from PIL import Image, ImageDraw
from sqlalchemy import select
from sqlalchemy.engine import make_url
from starlette.datastructures import Headers

from app.config import settings
from app.core.database import async_session, engine
from app.model_registry import load_models

load_models()

from app.modules.customers.models import Client, Site
from app.modules.customers.schemas import ClientCreate, SiteCreate
from app.modules.customers.service import ClientService, SiteService
from app.modules.identity.models import Role, User
from app.modules.interventions.models.intervention import Intervention
from app.modules.interventions.models.photo import PhotoUsage
from app.modules.interventions.schemas.intervention import InterventionCreate
from app.modules.interventions.services.intervention import InterventionService
from app.modules.interventions.services.photo import PhotoService

MARKER = "INT-111 backup recipe v1 — synthetic data"


async def populate(confirm_db):
    if make_url(settings.DATABASE_URL).database != confirm_db:
        raise RuntimeError("Database confirmation mismatch; no fixture created.")

    async with async_session() as db:
        admins = (await db.scalars(
            select(User).where(User.role == Role.ADMIN, User.is_active.is_(True))
        )).all()
        if len(admins) != 1:
            raise RuntimeError("Exactly one active administrator is required.")
        admin = admins[0]

        name = "TEST — Sauvegarde"
        client = (await db.scalars(
            select(Client).where(Client.full_name == name)
        )).one_or_none()
        if client is None:
            client = await ClientService(db).create_client(ClientCreate(
                full_name=name, phone="TEST-INT111",
                address="Adresse fictive — recette sauvegarde", notes=MARKER,
            ))
        elif client.notes != MARKER:
            raise RuntimeError("Client name collision; existing data left unchanged.")

        site = (await db.scalars(select(Site).where(
            Site.client_id == client.id, Site.name == "TEST — Site de recette"
        ))).one_or_none()
        if site is None:
            site = await SiteService(db).create_site(SiteCreate(
                client_id=client.id, name="TEST — Site de recette",
                address="Adresse fictive — recette sauvegarde", notes=MARKER,
            ))
        elif site.notes != MARKER:
            raise RuntimeError("Site name collision; existing data left unchanged.")

        print(f"Fixture client={client.id} site={site.id}", flush=True)
        for title, label, color in (
            ("TEST — Entretien", "TEST - entretien - INT-111", "#245078"),
            ("TEST — Dépannage", "TEST - depannage - INT-111", "#785024"),
        ):
            intervention = (await db.scalars(select(Intervention).where(
                Intervention.site_id == site.id, Intervention.title == title
            ))).one_or_none()
            if intervention is None:
                intervention = await InterventionService(db).create_intervention(
                    InterventionCreate(
                        site_id=site.id, title=title, description=MARKER,
                        scheduled_date=date.today(),
                    ), admin,
                )
            elif (intervention.description != MARKER
                  or intervention.technician_id != admin.id):
                raise RuntimeError("Intervention collision; existing data left unchanged.")

            service = PhotoService(db)
            photos = await service.list_photos(intervention.id)
            if not photos:
                image = Image.new("RGB", (640, 360), color)
                ImageDraw.Draw(image).text((30, 160), label, fill="white")
                buffer = io.BytesIO()
                image.save(buffer, "PNG")
                buffer.seek(0)
                upload = UploadFile(
                    file=buffer, filename="test-int111.png",
                    headers=Headers({"content-type": "image/png"}),
                )
                try:
                    await service.upload_photo(intervention.id, upload, PhotoUsage.OTHER)
                finally:
                    await upload.close()
                photos = await service.list_photos(intervention.id)

            for photo in photos:
                for url in (photo.file_url, photo.thumbnail_url):
                    if not url:
                        raise RuntimeError("Missing photo or thumbnail URL.")
                    path = Path(settings.UPLOAD_DIR) / "photos" / Path(url).name
                    with Image.open(path) as image:
                        image.verify()
                path = Path(settings.UPLOAD_DIR) / "photos" / Path(photo.file_url).name
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                print(
                    f"intervention={intervention.id} photo={photo.id} sha256={digest}",
                    flush=True,
                )
        print("Fixture ready; originals and thumbnails verified.", flush=True)


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm-db", required=True)
    args = parser.parse_args()
    try:
        await populate(args.confirm_db)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
