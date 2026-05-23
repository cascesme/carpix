from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import text  # noqa: F401
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
        raise NotImplementedError

    async def insert(
        self,
        brand_key: str,
        model_key: str,
        year: int,
        local_path: str,
        source_url: str,
        file_title: str,
    ) -> None:
        raise NotImplementedError
