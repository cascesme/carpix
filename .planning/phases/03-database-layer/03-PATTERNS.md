# Phase 3: Database Layer - Pattern Map

**Mapped:** 2026-05-23
**Files analyzed:** 9 new/modified files
**Analogs found:** 9 / 9 (all from parent project `/home/ccastro/Projects/auto-insight-claw/` and existing carpix source)

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `pyproject.toml` (modify) | config | — | `/home/ccastro/Projects/carpix/pyproject.toml` | exact (add 2 deps + 2 mypy overrides) |
| `alembic.ini` | config | — | `/home/ccastro/Projects/auto-insight-claw/alembic.ini` | exact |
| `alembic/env.py` | config | — | `/home/ccastro/Projects/auto-insight-claw/alembic/env.py` | exact (adapt: no ORM Base) |
| `alembic/script.py.mako` | config | — | `/home/ccastro/Projects/auto-insight-claw/alembic/script.py.mako` | exact (verbatim copy) |
| `alembic/versions/0001_create_vehicle_images.py` | migration | CRUD | `/home/ccastro/Projects/auto-insight-claw/alembic/versions/0001_create_jobs_table.py` | role-match |
| `src/carpix_images/infrastructure/__init__.py` | config | — | existing `__init__.py` files (empty) | exact |
| `src/carpix_images/infrastructure/cache_repository.py` | service | CRUD | `/home/ccastro/Projects/auto-insight-claw/src/auto_insight_claw/infrastructure/job_repository.py` | role-match |
| `src/carpix_images/main.py` (modify) | config | request-response | `/home/ccastro/Projects/carpix/src/carpix_images/main.py` | exact (fill lifespan stub) |
| `tests/conftest.py` (modify) | test | — | `/home/ccastro/Projects/auto-insight-claw/tests/integration/conftest.py` | exact |
| `tests/integration/__init__.py` | config | — | existing `__init__.py` files (empty) | exact |
| `tests/integration/test_cache_repository.py` | test | CRUD | `/home/ccastro/Projects/auto-insight-claw/tests/integration/test_migrations.py` | role-match |

---

## Pattern Assignments

### `pyproject.toml` (modify — add deps and mypy overrides)

**Analog:** `/home/ccastro/Projects/carpix/pyproject.toml` (current state)

**Current dependencies block** (lines 9-14 of existing file):
```toml
dependencies = [
    "fastapi>=0.136.1",
    "uvicorn[standard]>=0.47.0",
    "pydantic-settings>=2.14.1",
    "asyncpg>=0.31.0",
]
```

**Target — add `sqlalchemy>=2.0`:**
```toml
dependencies = [
    "fastapi>=0.136.1",
    "uvicorn[standard]>=0.47.0",
    "pydantic-settings>=2.14.1",
    "asyncpg>=0.31.0",
    "sqlalchemy>=2.0",
]
```

**Current dev extras** (lines 17-25 of existing file):
```toml
dev = [
    "pytest>=9.0.3",
    "pytest-asyncio>=1.3.0",
    "httpx>=0.28.1",
    "ruff>=0.15.14",
    "mypy>=2.1.0",
    "respx>=0.23.1",
    "testcontainers[postgres]>=4.14.2",
]
```

**Target — add `alembic>=1.18`:**
```toml
dev = [
    "pytest>=9.0.3",
    "pytest-asyncio>=1.3.0",
    "httpx>=0.28.1",
    "ruff>=0.15.14",
    "mypy>=2.1.0",
    "respx>=0.23.1",
    "testcontainers[postgres]>=4.14.2",
    "alembic>=1.18",
]
```

**Add mypy overrides for sqlalchemy and alembic** — mirror existing asyncpg override pattern (lines 43-48 of existing file):
```toml
[[tool.mypy.overrides]]
module = ["sqlalchemy", "sqlalchemy.*"]
ignore_missing_imports = true

[[tool.mypy.overrides]]
module = ["alembic", "alembic.*"]
ignore_missing_imports = true
```

**Note:** Check whether sqlalchemy 2.0.49 ships its own py.typed marker (it does). If mypy resolves types natively, the override is harmless but unnecessary — include it anyway for safety, consistent with the project pattern for third-party packages.

---

### `alembic.ini` (new — verbatim copy from parent project)

**Analog:** `/home/ccastro/Projects/auto-insight-claw/alembic.ini` (lines 1-40 — full file)

**Full file pattern:**
```ini
[alembic]
script_location = alembic
prepend_sys_path = .
path_separator = os
# URL is overridden by env.py from $DATABASE_URL
sqlalchemy.url = postgresql+asyncpg://placeholder:placeholder@localhost/placeholder

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

**Adaptation notes:** Copy verbatim. The placeholder URL is correct — `env.py` overrides it from `$DATABASE_URL` at runtime.

---

### `alembic/env.py` (new — adapted from parent, removing ORM dependency)

**Analog:** `/home/ccastro/Projects/auto-insight-claw/alembic/env.py` (lines 1-36 — full file)

**Parent project's env.py** (lines 1-36):
```python
import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from auto_insight_claw.infrastructure.models import Base   # <-- ORM-specific, remove

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata   # <-- ORM-specific, replace with None

_DATABASE_URL = os.environ["DATABASE_URL"]


def do_run_migrations(connection):  # type: ignore[no-untyped-def]
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    engine = create_async_engine(_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(do_run_migrations)
    await engine.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


run_migrations_online()
```

**Carpix adaptation** — remove ORM Base, set `target_metadata = None`:
```python
import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# No ORM autogenerate — migrations use op.create_table() directly
target_metadata = None

_DATABASE_URL = os.environ["DATABASE_URL"]


def do_run_migrations(connection):  # type: ignore[no-untyped-def]
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    engine = create_async_engine(_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(do_run_migrations)
    await engine.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


run_migrations_online()
```

**Key difference from parent:** No `from carpix_images.infrastructure.models import Base` — carpix uses Core-only `op.create_table()`, so there is no ORM `DeclarativeBase`.

---

### `alembic/script.py.mako` (new — verbatim copy)

**Analog:** `/home/ccastro/Projects/auto-insight-claw/alembic/script.py.mako` (lines 1-26 — full file)

**Full file pattern** (copy verbatim):
```mako
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
```

**Adaptation notes:** Copy verbatim. This is the Alembic default template.

---

### `alembic/versions/0001_create_vehicle_images.py` (new — migration)

**Analog:** `/home/ccastro/Projects/auto-insight-claw/alembic/versions/0001_create_jobs_table.py` (lines 1-44 — full file)

**Parent migration file structure** (lines 1-44):
```python
"""create jobs table

Revision ID: 0001
Revises:
Create Date: 2026-05-02

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "jobs",
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("brand", sa.String(), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("job_id"),
    )
    op.create_index("ix_jobs_brand_model_year", "jobs", ["brand", "model", "year"])
    op.create_index("ix_jobs_status", "jobs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_jobs_status", table_name="jobs")
    op.drop_index("ix_jobs_brand_model_year", table_name="jobs")
    op.drop_table("jobs")
```

**Carpix adaptation** — apply the same structure for `vehicle_images` table with composite PK:
```python
"""create vehicle_images table

Revision ID: 0001
Revises:
Create Date: 2026-05-23

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "vehicle_images",
        sa.Column("brand_key", sa.String(), nullable=False),
        sa.Column("model_key", sa.String(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("local_path", sa.Text(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("file_title", sa.Text(), nullable=False),
        sa.Column(
            "cached_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("brand_key", "model_key", "year"),
    )


def downgrade() -> None:
    op.drop_table("vehicle_images")
```

**Key differences from parent:**
- No `postgresql` dialect import (no UUID or JSONB columns)
- Composite PK: `sa.PrimaryKeyConstraint("brand_key", "model_key", "year")` instead of single-column PK
- `server_default=sa.func.now()` on `cached_at` — no `created_at`/`updated_at` split
- No secondary indexes needed (lookups are always by full composite PK)

---

### `src/carpix_images/infrastructure/__init__.py` (new — empty)

**Analog:** Any existing `__init__.py` in the project (e.g., `/home/ccastro/Projects/carpix/src/carpix_images/domain/__init__.py`)

**Pattern:** Empty file. No content, no imports. Required for Python package discovery.

---

### `src/carpix_images/infrastructure/cache_repository.py` (new — service, CRUD)

**Analog:** `/home/ccastro/Projects/auto-insight-claw/src/auto_insight_claw/infrastructure/job_repository.py`

**Import pattern from analog** (lines 1-13):
```python
import json
import uuid
from datetime import datetime

from auto_insight_claw.config import settings
from auto_insight_claw.domain.interfaces import DatabaseProtocol
from auto_insight_claw.domain.schemas import (
    AnalysisData,
    CompetitorVehicle,
    JobStatusEnum,
    JobStatusResponse,
)
```

**Repository class pattern from analog** (lines 25-31):
```python
class PostgreSQLJobRepository:
    def __init__(self, db: DatabaseProtocol) -> None:
        self._db = db
```

**find() method pattern from analog** (lines 29-61 — adapted to SQLAlchemy Core):
```python
# Analog uses asyncpg fetchrow(); carpix uses SQLAlchemy text() + conn.execute()
async def find_recent_job(
    self, brand_key: str, model_key: str, year: int, location: str
) -> AnalysisData | None:
    row = await self._db.fetchrow(
        "SELECT result FROM ...",
        brand_key, model_key, year, ...
    )
    if row is None:
        return None
    return AnalysisData.model_validate_json(row["result"])
```

**Carpix implementation** — use `AsyncEngine` + `text()` instead of `DatabaseProtocol`:
```python
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
                    "VALUES (:brand_key, :model_key, :year, :local_path, :source_url, :file_title) "
                    "ON CONFLICT DO NOTHING"
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
```

**Key differences from analog (job_repository.py):**
- `AsyncEngine` injected directly (not `DatabaseProtocol`) — simpler, no adapter layer needed
- `engine.connect()` for SELECT (read-only, no transaction overhead)
- `engine.begin()` for INSERT (auto-commit on success, auto-rollback on exception)
- `text()` with named params (`:brand_key`) instead of asyncpg positional params (`$1`)
- `@dataclass` for `CacheEntry` result type — no Pydantic model needed for a simple data holder
- `from __future__ import annotations` — matches parent project style convention

---

### `src/carpix_images/main.py` (modify — fill lifespan stub)

**Analog:** `/home/ccastro/Projects/carpix/src/carpix_images/main.py` (current state, lines 1-25)

**Current lifespan** (lines 9-12 — the stub to replace):
```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Phase 1: no-op. Phase 3 will wire asyncpg pool here.
    yield
```

**Target lifespan** — wire `create_async_engine` on startup, `dispose` on shutdown:
```python
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import cast

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from carpix_images.config import settings
from carpix_images.routers.health import router as health_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    engine = create_async_engine(settings.database_url)
    app.state.engine = engine
    try:
        yield
    finally:
        await engine.dispose()
```

**mypy note:** `app.state` is `starlette.datastructures.State` — attribute access returns `Any` under mypy strict. At call sites (future Phase 5/6), use `cast(AsyncEngine, request.app.state.engine)` or pass the engine explicitly into the repository constructor. The `cast` import is already listed above.

**Imports to add** (extend existing import block):
- `from typing import cast` — needed at call sites; import here for future use
- `from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine`

**Imports to keep unchanged:**
- `from collections.abc import AsyncGenerator`
- `from contextlib import asynccontextmanager`
- `from fastapi import FastAPI`
- `from carpix_images.routers.health import router as health_router`

---

### `tests/conftest.py` (modify — add postgres_container fixture)

**Analog:** `/home/ccastro/Projects/auto-insight-claw/tests/integration/conftest.py` (lines 1-14 — full file)

**Parent integration conftest** (lines 1-14):
```python
import os
from collections.abc import Generator

import pytest
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer


@pytest.fixture(scope="session")
def postgres_container() -> Generator[str, None, None]:
    with PostgresContainer("postgres:17", driver="asyncpg") as pg:
        url = pg.get_connection_url()
        os.environ["DATABASE_URL"] = url
        yield url


@pytest.fixture(scope="session")
def redis_container() -> Generator[str, None, None]:
    with RedisContainer("redis:8") as redis:
        ...
```

**Carpix adaptation** — add `postgres_container` to the existing `tests/conftest.py`:
```python
import os
from collections.abc import Generator

import pytest
from testcontainers.postgres import PostgresContainer

# Must run before any carpix_images module — Settings() reads env at import time.
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/testdb"
)


@pytest.fixture(scope="session")
def postgres_container() -> Generator[str, None, None]:
    with PostgresContainer("postgres:17", driver="asyncpg") as pg:
        url = pg.get_connection_url()
        os.environ["DATABASE_URL"] = url
        yield url
```

**Key details:**
- `scope="session"` — container starts once for the entire test run, shared across modules
- `driver="asyncpg"` — produces `postgresql+asyncpg://...` URL, matching SQLAlchemy format
- `os.environ["DATABASE_URL"] = url` (not `setdefault`) — overrides the unit-test default with the real container URL
- `yield url` — yields the URL string; fixtures that depend on `postgres_container` receive it
- The existing `os.environ.setdefault(...)` guard at top of file stays — it protects unit tests that run without the container

---

### `tests/integration/__init__.py` (new — empty)

**Analog:** `/home/ccastro/Projects/carpix/tests/__init__.py` (empty)

**Pattern:** Empty file. Required for pytest collection of the `tests/integration/` package.

---

### `tests/integration/test_cache_repository.py` (new — integration test)

**Analog:** `/home/ccastro/Projects/auto-insight-claw/tests/integration/test_migrations.py` (lines 1-255)

**Module-level fixture pinning pattern** (line 18 of analog):
```python
pytestmark = pytest.mark.usefixtures("postgres_container")
```

**Alembic config helper pattern** (lines 21-26 of analog):
```python
def _alembic_cfg() -> Config:
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])
    return cfg
```

**asyncpg URL helper pattern** (lines 28-30 of analog — used for raw schema verification):
```python
def _asyncpg_url() -> str:
    """Strip +asyncpg dialect prefix for raw asyncpg connections."""
    return os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")
```

**Sync migration fixture pattern** (lines 97-99 of analog):
```python
def test_upgrade_creates_jobs_table() -> None:
    url = _asyncpg_url()
    cfg = _alembic_cfg()
    command.upgrade(cfg, "head")
    assert asyncio.run(_table_exists(url, "jobs"))
```

**Async schema verification helper pattern** (lines 32-43 of analog):
```python
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
```

**Carpix full test file structure:**
```python
"""Integration tests for CacheRepository and Alembic migration.

Verifies:
- DB-01: vehicle_images table created with composite PK
- DB-02: find() returns CacheEntry or None; insert() is idempotent
- DB-03: AsyncEngine pool created on startup, disposed on shutdown
"""
from __future__ import annotations

import asyncio
import os

import asyncpg
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import create_async_engine

from carpix_images.infrastructure.cache_repository import CacheEntry, CacheRepository

pytestmark = pytest.mark.usefixtures("postgres_container")


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


@pytest.fixture(scope="module", autouse=True)
def run_migrations() -> None:
    command.upgrade(_alembic_cfg(), "head")


@pytest.fixture()
async def engine():  # type: ignore[return]
    e = create_async_engine(os.environ["DATABASE_URL"])
    yield e
    await e.dispose()


@pytest.fixture()
def repo(engine):  # type: ignore[return]
    yield CacheRepository(engine)


# DB-01: migration test (sync — Alembic command is synchronous)
def test_migration_creates_table() -> None:
    assert asyncio.run(_table_exists(_asyncpg_url(), "vehicle_images"))


# DB-02a: find returns entry
async def test_find_returns_entry(repo: CacheRepository) -> None:
    await repo.insert("toyota", "corolla", 2022, "/images/toyota/corolla/2022/image.jpg",
                      "https://commons.wikimedia.org/...", "Toyota_Corolla.jpg")
    entry = await repo.find("toyota", "corolla", 2022)
    assert entry is not None
    assert entry.brand_key == "toyota"
    assert entry.local_path == "/images/toyota/corolla/2022/image.jpg"


# DB-02b: find returns None when not found
async def test_find_returns_none(repo: CacheRepository) -> None:
    entry = await repo.find("unknown", "unknown", 9999)
    assert entry is None


# DB-02c: insert is idempotent
async def test_insert_idempotent(repo: CacheRepository) -> None:
    await repo.insert("honda", "civic", 2020, "/images/honda/civic/2020/image.jpg",
                      "https://commons.wikimedia.org/...", "Honda_Civic.jpg")
    # second insert must not raise
    await repo.insert("honda", "civic", 2020, "/images/honda/civic/2020/image.jpg",
                      "https://commons.wikimedia.org/...", "Honda_Civic.jpg")


# DB-03: pool lifecycle
async def test_pool_lifecycle() -> None:
    e = create_async_engine(os.environ["DATABASE_URL"])
    repo = CacheRepository(e)
    result = await repo.find("brand", "model", 2000)
    assert result is None  # table exists, row does not
    await e.dispose()  # must not raise
```

**Critical pattern details from analog:**
- `pytestmark = pytest.mark.usefixtures("postgres_container")` forces session fixture first (avoids fixture ordering bug — RESEARCH.md Pitfall 5)
- `run_migrations` is `def` (sync), NOT `async def` — Alembic `command.upgrade()` is synchronous (RESEARCH.md Pitfall 4)
- Schema verification uses `asyncio.run(_table_exists(...))` from sync test functions (same pattern as analog lines 102-103)
- `scope="module"` on `run_migrations` with `autouse=True` applies migration once per module
- `engine` fixture is `async` with `yield` — pytest-asyncio `asyncio_mode = "auto"` handles teardown

---

## Shared Patterns

### AsyncEngine `connect()` vs `begin()` Rule
**Source:** `src/carpix_images/infrastructure/cache_repository.py` (pattern from RESEARCH.md Anti-patterns)
**Apply to:** `cache_repository.py` (both methods)
```python
# READ operations — use connect() (no transaction overhead)
async with self._engine.connect() as conn:
    result = await conn.execute(text("SELECT ..."), params)

# WRITE operations — use begin() (auto-commit on success, auto-rollback on exception)
async with self._engine.begin() as conn:
    await conn.execute(text("INSERT ..."), params)
```

### `text()` Named Parameters (SQL Injection Prevention)
**Source:** `src/carpix_images/infrastructure/cache_repository.py`
**Apply to:** All SQL in `cache_repository.py`
```python
# CORRECT — named params, never f-string
text("SELECT ... WHERE brand_key = :brand_key"),
{"brand_key": brand_key}

# WRONG — never do this
text(f"SELECT ... WHERE brand_key = '{brand_key}'")
```

### Sync Alembic in Sync pytest Fixtures
**Source:** `/home/ccastro/Projects/auto-insight-claw/tests/integration/test_migrations.py` lines 97-103
**Apply to:** `tests/integration/test_cache_repository.py`
```python
# CORRECT — sync fixture calling sync Alembic command
@pytest.fixture(scope="module", autouse=True)
def run_migrations() -> None:
    command.upgrade(_alembic_cfg(), "head")

# WRONG — async fixture would block event loop
@pytest.fixture(scope="module", autouse=True)
async def run_migrations() -> None:   # DO NOT DO THIS
    command.upgrade(_alembic_cfg(), "head")
```

### `from __future__ import annotations`
**Source:** `/home/ccastro/Projects/auto-insight-claw/src/auto_insight_claw/infrastructure/job_repository.py` line 1
**Apply to:** `src/carpix_images/infrastructure/cache_repository.py`
```python
from __future__ import annotations
```

### `-> None` Return Type on All Test Functions
**Source:** `/home/ccastro/Projects/auto-insight-claw/tests/integration/test_migrations.py` (all test functions)
**Apply to:** All test functions in `tests/integration/test_cache_repository.py`
```python
def test_something() -> None:
    ...
```

### DSN Scheme Stripping for raw asyncpg
**Source:** `/home/ccastro/Projects/carpix/src/carpix_images/routers/health.py` line 12
**Apply to:** `tests/integration/test_cache_repository.py` `_asyncpg_url()` helper
```python
def _asyncpg_url() -> str:
    return os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")
```

---

## No Analog Found

None — all files have direct or role-match analogs.

---

## Metadata

**Analog search scope:**
- `/home/ccastro/Projects/carpix/src/carpix_images/` — existing carpix source (main.py, config.py, routers/health.py)
- `/home/ccastro/Projects/carpix/tests/` — existing carpix tests
- `/home/ccastro/Projects/auto-insight-claw/alembic/` — Alembic config, env, mako, migration versions
- `/home/ccastro/Projects/auto-insight-claw/src/auto_insight_claw/infrastructure/` — repository pattern
- `/home/ccastro/Projects/auto-insight-claw/tests/integration/` — integration test patterns

**Files scanned (carpix project):** 6
- `src/carpix_images/main.py`
- `src/carpix_images/config.py`
- `src/carpix_images/routers/health.py`
- `tests/conftest.py`
- `tests/unit/test_health.py`
- `pyproject.toml`

**Files scanned (parent project):** 7
- `alembic.ini`
- `alembic/env.py`
- `alembic/script.py.mako`
- `alembic/versions/0001_create_jobs_table.py`
- `src/auto_insight_claw/infrastructure/db.py`
- `src/auto_insight_claw/infrastructure/job_repository.py`
- `tests/integration/conftest.py`
- `tests/integration/test_migrations.py`
- `tests/integration/test_archive_integration.py`

**Pattern extraction date:** 2026-05-23
