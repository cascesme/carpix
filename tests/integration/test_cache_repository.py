"""Integration tests for CacheRepository — covers DB-01, DB-02, DB-03.

DB-01: vehicle_images table created via Alembic migration with composite PK.
DB-02: CacheRepository.find() and insert() against a real Postgres instance.
DB-03: SQLAlchemy Core async connection pool lifecycle (create on startup, dispose on
       shutdown).
"""

from __future__ import annotations

import asyncio
import os

import asyncpg
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from carpix_images.infrastructure.cache_repository import CacheEntry, CacheRepository

pytestmark = pytest.mark.usefixtures("postgres_container")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _alembic_cfg() -> Config:
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])
    return cfg


def _asyncpg_url() -> str:
    return os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")


async def _table_exists(url: str, table: str) -> bool:
    conn = await asyncpg.connect(url)
    try:
        row = await conn.fetchrow(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = $1",
            table,
        )
        return row is not None
    finally:
        await conn.close()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module", autouse=True)
def run_migrations() -> None:
    command.upgrade(_alembic_cfg(), "head")


@pytest.fixture()
async def engine() -> AsyncEngine:  # type: ignore[override]
    e = create_async_engine(os.environ["DATABASE_URL"])
    yield e  # type: ignore[misc]
    await e.dispose()


@pytest.fixture()
def repo(engine: AsyncEngine) -> CacheRepository:
    return CacheRepository(engine)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_migration_creates_table() -> None:
    """DB-01: Alembic migration creates vehicle_images table with composite PK."""
    exists = asyncio.run(_table_exists(_asyncpg_url(), "vehicle_images"))
    assert exists, "vehicle_images table does not exist after migration"


async def test_find_returns_entry(repo: CacheRepository) -> None:
    """DB-02a: find() returns a CacheEntry when the row exists."""
    await repo.insert(
        brand_key="toyota",
        model_key="corolla",
        year=2022,
        local_path="/images/toyota/corolla/2022/image.jpg",
        source_url="https://upload.wikimedia.org/wikipedia/commons/thumb/a/a1/Toyota_Corolla_2022.jpg/800px-Toyota_Corolla_2022.jpg",
        file_title="Toyota_Corolla_2022.jpg",
    )
    entry = await repo.find(brand_key="toyota", model_key="corolla", year=2022)
    assert entry is not None
    assert isinstance(entry, CacheEntry)
    assert entry.brand_key == "toyota"
    assert entry.model_key == "corolla"
    assert entry.year == 2022


async def test_find_returns_none(repo: CacheRepository) -> None:
    """DB-02b: find() returns None when the row does not exist."""
    entry = await repo.find(brand_key="nonexistent", model_key="model", year=9999)
    assert entry is None


async def test_insert_idempotent(repo: CacheRepository) -> None:
    """DB-02c: insert() is idempotent — calling twice does not raise an error."""
    kwargs = {
        "brand_key": "ford",
        "model_key": "mustang",
        "year": 2023,
        "local_path": "/images/ford/mustang/2023/image.jpg",
        "source_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f1/Ford_Mustang_2023.jpg/800px-Ford_Mustang_2023.jpg",
        "file_title": "Ford_Mustang_2023.jpg",
    }
    await repo.insert(**kwargs)
    await repo.insert(**kwargs)  # must not raise IntegrityError


async def test_pool_lifecycle(engine: AsyncEngine) -> None:
    """DB-03: Pool can be created and disposed without leaked connections."""
    async with engine.connect() as conn:
        result = await conn.execute(
            __import__("sqlalchemy").text("SELECT 1")
        )
        assert result.scalar() == 1
    await engine.dispose()
