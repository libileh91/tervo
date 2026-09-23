"""
Tervo — Photo Service.

Business logic for photo upload/delete with thumbnail generation.
"""

import os
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.repositories.photo import PhotoRepository

# Formats MIME acceptés — WebP inclus pour Android / Chrome mobile
# HEIC est refusé volontairement (pas de support natif dans Pillow)
ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


class PhotoService:
    """Encapsulates business rules for photo management."""

    def __init__(self, db: AsyncSession):
        self.repo = PhotoRepository(db)
        self.db = db

    async def upload_photo(self, intervention_id: int, file: UploadFile, category: str) -> dict:
        """Upload a photo, generate thumbnail, save to DB."""

        # Validate content type
        content_type = file.content_type or "application/octet-stream"
        if content_type not in ALLOWED_CONTENT_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Format non accepté : {content_type}. Utilisez JPEG, PNG ou WebP.",
            )

        # Read file content
        content = await file.read()

        # Validate file size
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Fichier trop volumineux (max 10 Mo)",
            )

        # Generate unique filename
        file_uuid = uuid.uuid4().hex
        filename = f"{file_uuid}.jpg"
        thumb_filename = f"thumb_{file_uuid}.jpg"

        # Ensure upload directory exists
        upload_dir = Path(settings.UPLOAD_DIR) / "photos"
        upload_dir.mkdir(parents=True, exist_ok=True)

        file_path = upload_dir / filename
        thumb_path = upload_dir / thumb_filename

        # Save original file
        with open(file_path, "wb") as f:
            f.write(content)

        # Generate thumbnail with Pillow
        try:
            from PIL import Image
        except ImportError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Pillow (bibliothèque d'images) n'est pas installé. Contactez l'administrateur.",
            )

        try:
            img = Image.open(file_path)
            # Convert RGBA/PA/P modes to RGB before saving as JPEG
            if img.mode in ("RGBA", "LA", "P", "PA"):
                background = Image.new("RGB", img.size, (255, 255, 255))
                background.paste(
                    img, mask=img.split()[-1] if img.mode in ("RGBA", "PA") else None
                )
                img = background
            elif img.mode != "RGB":
                img = img.convert("RGB")

            img.thumbnail((300, 300))
            img.save(thumb_path, "JPEG", quality=85)
        except Exception:
            # If thumbnail fails, remove original and raise error
            os.remove(file_path)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Impossible de générer la miniature. Vérifiez le fichier.",
            )

        # Save to DB
        photo = await self.repo.create(
            {
                "intervention_id": intervention_id,
                "category": category,
                "file_path": str(file_path),
                "thumbnail_path": str(thumb_path),
            }
        )

        return {
            "id": photo.id,
            "category": photo.category,
            "file_url": f"{settings.UPLOAD_URL}/photos/{filename}",
            "thumbnail_url": f"{settings.UPLOAD_URL}/photos/{thumb_filename}",
            "taken_at": photo.taken_at.isoformat() if photo.taken_at else None,
        }

    async def delete_photo(self, photo_id: int) -> None:
        """Delete a photo: remove files from disk, then remove DB entry."""
        photo = await self.repo.get_by_id(photo_id)
        if photo is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Photo non trouvée",
            )

        # Remove files from disk (graceful if file already deleted)
        for path in [photo.file_path, photo.thumbnail_path]:
            if path and os.path.exists(path):
                os.remove(path)

        # Remove DB entry
        await self.repo.delete(photo)
