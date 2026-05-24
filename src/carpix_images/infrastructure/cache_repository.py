from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


@dataclass
class CacheEntry:
    brand_key: str
    model_key: str
    year: int
    local_path: str
    source_url: str
    file_title: str
    cached_at: datetime


class CacheRepository:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def find(
        self, brand_key: str, model_key: str, year: int
    ) -> CacheEntry | None:
        async with self._engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT brand_key, model_key, year, local_path, "
                    "source_url, file_title, cached_at "
                    "FROM vehicle_images "
                    "WHERE brand_key = :brand_key "
                    "AND model_key = :model_key "
                    "AND year = :year"
                ),
                {"brand_key": brand_key, "model_key": model_key, "year": year},
            )
            row = result.fetchone()
        if row is None:
            return None
        return CacheEntry(
            brand_key=row.brand_key,
            model_key=row.model_key,
            year=row.year,
            local_path=row.local_path,
            source_url=row.source_url,
            file_title=row.file_title,
            cached_at=row.cached_at,
        )

    async def insert(
        self,
        brand_key: str,
        model_key: str,
        year: int,
        local_path: str,
        source_url: str,
        file_title: str,
    ) -> None:
        async with self._engine.begin() as conn:
            await conn.execute(
                text(
                    "INSERT INTO vehicle_images "
                    "(brand_key, model_key, year, local_path, source_url, file_title) "
                    "VALUES (:brand_key, :model_key, :year, "
                    ":local_path, :source_url, :file_title) "
                    "ON CONFLICT (brand_key, model_key, year) DO UPDATE SET "
                    "local_path = EXCLUDED.local_path, "
                    "source_url = EXCLUDED.source_url, "
                    "file_title = EXCLUDED.file_title, "
                    "cached_at = now()"
                ),
                {
                    "brand_key": brand_key,
                    "model_key": model_key,
                    "year": year,
                    "local_path": local_path,
                    "source_url": source_url,
                    "file_title": file_title,
                },
            )
