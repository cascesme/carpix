"""Unit tests for ImageService — RED baseline for CACHE-01..CACHE-04."""

from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
import respx
from fastapi import HTTPException
from fastapi.responses import FileResponse

from carpix_images.infrastructure.cache_repository import CacheEntry
from carpix_images.services.image_service import ImageService


def _make_cache_entry() -> CacheEntry:
    return CacheEntry(
        brand_key="toyota",
        model_key="corolla",
        year=2022,
        local_path="/images/toyota/corolla/2022/image.jpg",
        source_url="https://upload.wikimedia.org/sample.jpg",
        file_title="Toyota_Corolla_2022.jpg",
        cached_at=datetime(2024, 1, 1, 0, 0, 0),
    )


def _make_service(
    *,
    repo_find_return: CacheEntry | None = None,
    repo_find_side_effect: list[CacheEntry | None] | None = None,
    wikimedia_return: str | None = None,
    storage_file_response_return: FileResponse | None = None,
    storage_file_response_side_effect: list[FileResponse | Exception] | None = None,
    storage_save_return: Path | None = None,
) -> ImageService:
    storage = MagicMock()
    if storage_file_response_side_effect is not None:
        storage.file_response.side_effect = storage_file_response_side_effect
    else:
        storage.file_response.return_value = (
            storage_file_response_return
            if storage_file_response_return is not None
            else MagicMock(spec=FileResponse)
        )
    default_path = Path("/images/toyota/corolla/2022/image.jpg")
    storage.save = AsyncMock(return_value=storage_save_return or default_path)

    repo = MagicMock()
    if repo_find_side_effect is not None:
        repo.find = AsyncMock(side_effect=repo_find_side_effect)
    else:
        repo.find = AsyncMock(return_value=repo_find_return)
    repo.insert = AsyncMock(return_value=None)

    wikimedia = MagicMock()
    wikimedia.find_jpeg_url = AsyncMock(return_value=wikimedia_return)

    return ImageService(
        storage=storage,
        repo=repo,
        wikimedia=wikimedia,
        http_client=httpx.AsyncClient(),
    )


async def test_cache_hit_returns_file_response_without_wikimedia_call() -> None:
    """CACHE-01: cache hit returns FileResponse, no Wikimedia call."""
    expected_response = MagicMock(spec=FileResponse)
    svc = _make_service(
        repo_find_return=_make_cache_entry(),
        storage_file_response_return=expected_response,
    )

    response, cache_hit = await svc.get_or_fetch("toyota", "corolla", 2022)

    assert isinstance(response, FileResponse)
    assert cache_hit is True
    svc._wikimedia.find_jpeg_url.assert_not_called()  # type: ignore[attr-defined]


async def test_cache_miss_fetches_saves_inserts_and_returns_file_response(
    respx_mock: respx.MockRouter,
) -> None:
    """CACHE-02: cache miss triggers full fetch → save → insert → FileResponse."""
    thumb_url = "https://upload.wikimedia.org/sample.jpg"
    respx_mock.get(thumb_url).respond(200, content=b"JPEG_BYTES")

    expected_response = MagicMock(spec=FileResponse)
    svc = _make_service(
        repo_find_return=None,
        wikimedia_return=thumb_url,
        storage_file_response_return=expected_response,
    )

    response, cache_hit = await svc.get_or_fetch("toyota", "corolla", 2022)

    assert isinstance(response, FileResponse)
    assert cache_hit is False
    svc._storage.save.assert_called_once()  # type: ignore[attr-defined]
    svc._repo.insert.assert_called_once()  # type: ignore[attr-defined]


async def test_concurrent_requests_for_same_key_trigger_exactly_one_wikimedia_fetch(
    respx_mock: respx.MockRouter,
) -> None:
    """CACHE-03: per-key lock ensures only one Wikimedia fetch for concurrent reqs."""
    thumb_url = "https://upload.wikimedia.org/sample.jpg"
    respx_mock.get(thumb_url).respond(200, content=b"JPEG_BYTES")

    entry = _make_cache_entry()
    # First call returns None (miss), subsequent calls return cached entry
    svc = _make_service(
        repo_find_side_effect=[None, entry],
        wikimedia_return=thumb_url,
    )

    responses = await asyncio.gather(
        svc.get_or_fetch("toyota", "corolla", 2022),
        svc.get_or_fetch("toyota", "corolla", 2022),
    )

    (r0, hit0), (r1, hit1) = responses
    assert isinstance(r0, FileResponse)
    assert isinstance(r1, FileResponse)
    assert svc._wikimedia.find_jpeg_url.call_count == 1  # type: ignore[attr-defined]


async def test_self_healing_when_db_hit_but_file_absent(
    respx_mock: respx.MockRouter,
) -> None:
    """CACHE-04a: DB hit but file missing → re-fetch and return FileResponse."""
    thumb_url = "https://upload.wikimedia.org/sample.jpg"
    respx_mock.get(thumb_url).respond(200, content=b"JPEG_BYTES")

    good_response = MagicMock(spec=FileResponse)
    # First file_response call raises FileNotFoundError; second returns normally
    svc = _make_service(
        repo_find_return=_make_cache_entry(),
        wikimedia_return=thumb_url,
        storage_file_response_side_effect=[FileNotFoundError("missing"), good_response],
    )

    response, cache_hit = await svc.get_or_fetch("toyota", "corolla", 2022)

    assert isinstance(response, FileResponse)
    assert cache_hit is False
    svc._wikimedia.find_jpeg_url.assert_called_once()  # type: ignore[attr-defined]


async def test_raises_http_exception_404_when_no_image_found() -> None:
    """CACHE-04b: Wikimedia returns None → 404 HTTPException raised."""
    svc = _make_service(
        repo_find_return=None,
        wikimedia_return=None,
    )

    with pytest.raises(HTTPException) as exc_info:
        await svc.get_or_fetch("nonexistent", "vehicle", 9999)

    assert exc_info.value.status_code == 404
