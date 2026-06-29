"""
Unit tests for ChecklistService.validate_all_checked().

Run:
    cd backend/
    .venv/bin/python -m pytest tests/test_checklist_service.py -v
"""

from unittest.mock import AsyncMock

import pytest
from app.services.checklist import ChecklistService


@pytest.fixture
def db_mock():
    return AsyncMock()


@pytest.fixture
def service(db_mock):
    srv = ChecklistService(db_mock)
    srv.repo = AsyncMock()
    return srv


@pytest.mark.asyncio
async def test_all_checked(service):
    service.repo.count_unchecked_by_category = AsyncMock(return_value={})
    result = await service.validate_all_checked(1)
    assert result["is_valid"] is True
    assert result["errors"] == []


@pytest.mark.asyncio
async def test_some_unchecked(service):
    service.repo.count_unchecked_by_category = AsyncMock(
        return_value={"pre_intervention": 1, "post_intervention": 1}
    )
    result = await service.validate_all_checked(1)
    assert result["is_valid"] is False
    assert len(result["errors"]) == 2
    assert "pré-intervention" in result["errors"][0]
    assert "post-intervention" in result["errors"][1]
    assert "2 items non cochés" in result["detail"]


@pytest.mark.asyncio
async def test_only_pre_unchecked(service):
    service.repo.count_unchecked_by_category = AsyncMock(
        return_value={"pre_intervention": 2}
    )
    result = await service.validate_all_checked(1)
    assert result["is_valid"] is False
    assert len(result["errors"]) == 1


@pytest.mark.asyncio
async def test_only_post_unchecked(service):
    service.repo.count_unchecked_by_category = AsyncMock(
        return_value={"post_intervention": 1}
    )
    result = await service.validate_all_checked(1)
    assert result["is_valid"] is False
    assert len(result["errors"]) == 1
