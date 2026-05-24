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

_USER_AGENT = "carpix-images/0.1 (https://github.com/user/carpix)"

class ImageService:
    def __init__(
        self,
        storage: StorageService,
        repo: CacheRepository,
        wikimedia: WikimediaClient,
        http_client: httpx.AsyncClient,
    ) -> None:
        self._storage = storage
        self._repo = repo
        self._wikimedia = wikimedia
        self._http_client = http_client
        self._locks: dict[tuple[str, str, int], asyncio.Lock] = {}

    async def get_or_fetch(
        self, brand: str, model: str, year: int
    ) -> tuple[FileResponse, bool]:
        brand_key = canonical_key(brand)
        model_key = canonical_key(model)

        lock_key = (brand_key, model_key, year)
        if lock_key not in self._locks:
            self._locks[lock_key] = asyncio.Lock()
        async with self._locks[lock_key]:
            entry = await self._repo.find(brand_key, model_key, year)
            if entry is not None:
                try:
                    return self._storage.file_response(brand_key, model_key, year), True
                except FileNotFoundError:
                    pass  # self-healing: fall through to re-fetch

            url = await self._wikimedia.find_jpeg_url(brand, model, year)
            if url is None:
                raise HTTPException(
                    status_code=404,
                    detail="No image found for this vehicle",
                )

            try:
                response = await self._http_client.get(url, timeout=httpx.Timeout(30.0), headers={"User-Agent": _USER_AGENT})
                response.raise_for_status()
            except (httpx.HTTPStatusError, httpx.RequestError):
                raise HTTPException(
                    status_code=404,
                    detail="No image found for this vehicle",
                )
            image_bytes: bytes = response.content

            saved_path: Path = await self._storage.save(
                brand_key, model_key, year, image_bytes
            )
            file_title: str = url.rsplit("/", 1)[-1]
            await self._repo.insert(
                brand_key,
                model_key,
                year,
                local_path=str(saved_path),
                source_url=url,
                file_title=file_title,
            )
            return self._storage.file_response(brand_key, model_key, year), False
