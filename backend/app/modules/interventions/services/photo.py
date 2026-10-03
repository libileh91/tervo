"""Photo storage, validation and parent-scoped persistence."""

import io
import logging
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.modules.interventions.models.photo import PhotoUsage
from app.modules.interventions.repositories.photo import PhotoRepository
from app.modules.interventions.schemas.intervention import PhotoRef

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024
logger = logging.getLogger(__name__)


class PhotoService:
    def __init__(self, db: AsyncSession):
        self.repo = PhotoRepository(db)
        self.db = db

    async def list_photos(self, intervention_id: int) -> list[PhotoRef]:
        return [PhotoRef.model_validate(p) for p in await self.repo.list_by_intervention(intervention_id)]

    async def upload_photo(self, intervention_id: int, file: UploadFile, usage: PhotoUsage) -> PhotoRef:
        if file.content_type not in ALLOWED_CONTENT_TYPES:
            raise HTTPException(400, "Format non accepté. Utilisez JPEG, PNG ou WebP.")
        content = await file.read(MAX_FILE_SIZE + 1)
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(400, "Fichier trop volumineux (max 10 Mo)")
        try:
            with Image.open(io.BytesIO(content)) as original:
                if original.format not in {"JPEG", "PNG", "WEBP"}:
                    raise ValueError("Unsupported image")
                original.load()
                if original.mode in ("RGBA", "LA", "P", "PA"):
                    rgba = original.convert("RGBA")
                    image = Image.new("RGB", original.size, (255, 255, 255))
                    image.paste(rgba, mask=rgba.getchannel("A"))
                else:
                    image = original.convert("RGB")
                image.thumbnail((300, 300))
                thumbnail = io.BytesIO()
                image.save(thumbnail, "JPEG", quality=85)
        except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
            raise HTTPException(400, "Impossible de générer la miniature. Vérifiez le fichier.")

        upload_dir = Path(settings.UPLOAD_DIR) / "photos"
        upload_dir.mkdir(parents=True, exist_ok=True)
        token = uuid.uuid4().hex
        extension = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}[file.content_type]
        file_path = upload_dir / f"{token}.{extension}"
        thumb_path = upload_dir / f"thumb_{token}.jpg"
        created: list[Path] = []
        try:
            for path, data in ((file_path, content), (thumb_path, thumbnail.getvalue())):
                # Exclusive creation makes cleanup ownership unambiguous.
                with path.open("xb") as target:
                    created.append(path)
                    target.write(data)
            photo = await self.repo.create({
                "intervention_id": intervention_id,
                "usage": usage,
                "file_path": str(file_path),
                "thumbnail_path": str(thumb_path),
            })
            # Validate the response while the row can still be rolled back.
            response = PhotoRef.model_validate(photo)
            await self.db.commit()
        except BaseException:
            try:
                await self.db.rollback()
            finally:
                for path in created:
                    try:
                        path.unlink(missing_ok=True)
                    except OSError:
                        logger.exception("Failed to clean up upload file %s", path)
            raise
        return response

    async def delete_photo(self, intervention_id: int, photo_id: int) -> None:
        photo = await self.repo.get_by_id(intervention_id, photo_id)
        if photo is None:
            raise HTTPException(404, "Photo non trouvée")
        root = Path(settings.UPLOAD_DIR).resolve()
        paths = []
        for raw in (photo.file_path, photo.thumbnail_path):
            if raw:
                path = Path(raw).resolve()
                if not path.is_relative_to(root) or path == root:
                    raise HTTPException(400, "Chemin de photo invalide")
                paths.append(path)
        await self.repo.delete(photo)
        for path in paths:
            path.unlink(missing_ok=True)
