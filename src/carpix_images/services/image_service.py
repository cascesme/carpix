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
    ) -> FileResponse:
        brand_key = canonical_key(brand)
        model_key = canonical_key(model)

        lock_key = (brand_key, model_key, year)
        if lock_key not in self._locks:
            self._locks[lock_key] = asyncio.Lock()

        async with self._locks[lock_key]:
            # Step a: check DB cache
            entry = await self._repo.find(brand_key, model_key, year)

            # Step b: cache hit — attempt to serve from local file
            if entry is not None:
                try:
                    return self._storage.file_response(brand_key, model_key, year)
                except FileNotFoundError:
                    # Self-healing: file missing on disk, fall through to re-fetch
                    pass

            # Step c: cache miss or self-healing — fetch from Wikimedia
            url = await self._wikimedia.find_jpeg_url(brand, model, year)
            if url is None:
                raise HTTPException(
                    status_code=404,
                    detail="No image found for this vehicle",
                )

            # Step d: download image
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=httpx.Timeout(30.0))
                response.raise_for_status()
                image_bytes: bytes = response.content

            # Step e: save to disk
            saved_path: Path = await self._storage.save(
                brand_key, model_key, year, image_bytes
            )

            # Step f: extract file title from URL
            file_title: str = url.rsplit("/", 1)[-1]

            # Step g: insert DB record
            await self._repo.insert(
                brand_key,
                model_key,
                year,
                local_path=str(saved_path),
                source_url=url,
                file_title=file_title,
            )

            # Step h: return FileResponse
            return self._storage.file_response(brand_key, model_key, year)
