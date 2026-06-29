"""
Tests for services — targeting uncovered logic.

Run:
    cd backend/
    uv run pytest tests/test_services.py -v --cov=app --cov-report=term-missing
"""

from datetime import date, datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.services.checklist import ChecklistService
from app.services.photo import PhotoService


class TestChecklistService:
    """Targets uncovered lines in checklist_service and checklist_repo."""

    @pytest.fixture
    def db_mock(self):
        return AsyncMock()

    @pytest.fixture
    def service(self, db_mock):
        srv = ChecklistService(db_mock)
        srv.repo = AsyncMock()
        return srv

    async def test_validate_all_checked_valid(self, service):
        """All checked → is_valid."""
        service.repo.count_unchecked_by_category = AsyncMock(return_value={})
        result = await service.validate_all_checked(1)
        assert result["is_valid"] is True
        assert result["errors"] == []

    async def test_validate_all_checked_partial(self, service):
        """Some unchecked → is_valid=False."""
        service.repo.count_unchecked_by_category = AsyncMock(
            return_value={"pre_intervention": 1}
        )
        result = await service.validate_all_checked(1)
        assert result["is_valid"] is False
        assert len(result["errors"]) == 1
        assert "pré-intervention" in result["errors"][0]

    async def test_update_item(self, service):
        """update_item → calls repo methods."""
        service.repo.get_item = AsyncMock()
        service.repo.update_item = AsyncMock()
        await service.update_item(1, {"checked": True})
        service.repo.get_item.assert_awaited_once_with(1)
        service.repo.update_item.assert_awaited_once()


class TestPhotoService:
    """Targets uncovered constants in photo_service."""

    def test_allowed_formats(self):
        """Allowed content types match valid image formats."""
        from app.services.photo import ALLOWED_CONTENT_TYPES, MAX_FILE_SIZE

        assert "image/jpeg" in ALLOWED_CONTENT_TYPES
        assert "image/png" in ALLOWED_CONTENT_TYPES
        assert "image/webp" in ALLOWED_CONTENT_TYPES
        assert MAX_FILE_SIZE == 10 * 1024 * 1024
