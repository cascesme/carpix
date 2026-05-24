from __future__ import annotations

import asyncio
from pathlib import Path

import httpx
from fastapi import HTTPException
from fastapi.responses import FileResponse

from carpix_images.domain.normalize import canonical_key
from carpix_images.infrastructure.cache_repository import CacheRepository
from carpix_images.services.storage import StorageService
from carpix_images.services.wikimedia import WikimediaClient


class ImageService:
    def __init__(
        self,
        storage: StorageService,
        repo: CacheRepository,
        wikimedia: WikimediaClient,
    ) -> None:
        self._storage = storage
        self._repo = repo
        self._wikimedia = wikimedia
        self._locks: dict[tuple[str, str, int], asyncio.Lock] = {}

    async def get_or_fetch(
        self, brand: str, model: str, year: int
    ) -> tuple[FileResponse, bool]:
        raise NotImplementedError
