# Phase 3: Database Layer - Research

**Researched:** 2026-05-23
**Domain:** SQLAlchemy 2.0 async, Alembic migrations, asyncpg connection pool, testcontainers integration
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DB-01 | `vehicle_images` table via Alembic migration with composite PK `(brand_key, model_key, year)` and columns `local_path`, `source_url`, `file_title`, `cached_at` | Alembic `op.create_table()` pattern confirmed from parent project; composite PK via `sa.PrimaryKeyConstraint` |
| DB-02 | `CacheRepository.find()` by composite PK; idempotent `insert()` via `INSERT ... ON CONFLICT DO NOTHING` | SQLAlchemy Core `text()` + `AsyncConnection.execute()` confirmed; `ON CONFLICT DO NOTHING` is standard Postgres syntax |
| DB-03 | asyncpg + SQLAlchemy Core connection pool as lifespan-scoped singleton; created on startup, closed on shutdown | `create_async_engine()` + FastAPI lifespan `@asynccontextmanager` confirmed; `await engine.dispose()` on shutdown |
</phase_requirements>

---

## Summary

Phase 3 wires Postgres into the carpix-images microservice: an Alembic migration creates the `vehicle_images` table, a `CacheRepository` wraps async SQL against it, and the SQLAlchemy connection pool is initialised inside the FastAPI lifespan context manager that was stubbed out in Phase 1.

The project already has `asyncpg>=0.31.0` in its production dependencies and `testcontainers[postgres]>=4.14.2` in dev. The missing production deps are `sqlalchemy>=2.0` and the missing dev dep is `alembic>=1.18`. Both are legitimate, well-maintained packages (slopcheck: OK, PyPI registry confirmed). The parent project (`auto-insight-claw`) provides an exact template for every artefact this phase must produce: `alembic.ini`, `alembic/env.py`, `alembic/versions/000N_*.py`, and the integration-test conftest fixture.

The CacheRepository will use SQLAlchemy Core exclusively — no ORM, no models.py — querying via `text()` and `AsyncConnection.execute()`. The migration uses `op.create_table()` directly; there is no need for a `DeclarativeBase` or autogenerate setup. Pool injection into the repository follows the module-level singleton pattern already established in the parent project's `db.py`, adapted to store the `AsyncEngine` on `app.state` inside the lifespan context manager (the comment on line 11 of `main.py` already reserves this slot for Phase 3).

**Primary recommendation:** Add `sqlalchemy>=2.0` to `[project].dependencies` and `alembic>=1.18` to `[project.optional-dependencies].dev` in `pyproject.toml`. Mirror the parent project's `alembic.ini` + `alembic/env.py` verbatim, adapting the import path. Write the migration with `op.create_table()`, write `CacheRepository` using `text()` queries, and store the pool on `app.state.engine` inside the lifespan context manager.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Alembic migration (schema creation) | Database / Storage | — | DDL lives in the DB tier; applied at deploy time, not request time |
| Connection pool lifecycle | API / Backend (lifespan) | — | Pool is a process-scoped resource created/disposed in FastAPI's lifespan context |
| `CacheRepository.find()` / `insert()` | API / Backend (infrastructure) | Database / Storage | Repository is a Python class in the backend; SQL executes in Postgres |
| Pool injection to repository | API / Backend (DI) | — | `app.state.engine` accessed from request scope or passed explicitly at call site |
| Integration tests (schema + data) | Test harness | Database / Storage | testcontainers spins a real Postgres; Alembic migrations applied in fixture |

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| sqlalchemy | 2.0.49 [VERIFIED: PyPI registry] | Async connection pool + `text()` query execution | First-class asyncpg support; `create_async_engine("postgresql+asyncpg://...")` |
| alembic | 1.18.4 [VERIFIED: PyPI registry] | Schema migration | Canonical SQLAlchemy migration tool; same version as parent project |
| asyncpg | 0.31.0 [VERIFIED: PyPI registry] | Postgres async driver (already in deps) | Pure-async, no thread-pool overhead; already used for health probe |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| testcontainers[postgres] | 4.14.2 [VERIFIED: PyPI registry] | Real Postgres in integration tests (already in dev deps) | CacheRepository integration tests |

### Installation

Add to `pyproject.toml`:

```toml
# [project].dependencies — add:
"sqlalchemy>=2.0",

# [project.optional-dependencies].dev — add:
"alembic>=1.18",
```

Then sync:
```bash
uv sync
```

**Version verification:** All versions confirmed against PyPI registry via `pip index versions` on 2026-05-23. SQLAlchemy 2.0.49 and Alembic 1.18.4 are the current latest stable releases.

---

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| sqlalchemy | PyPI | ~20 yrs | Very high (100M+/mo) | github.com/sqlalchemy/sqlalchemy | OK | Approved |
| alembic | PyPI | ~12 yrs | Very high | github.com/sqlalchemy/alembic | OK | Approved |
| asyncpg | PyPI | ~8 yrs | High | github.com/MagicStack/asyncpg | OK | Approved (already in project) |
| testcontainers | PyPI | ~7 yrs | High | github.com/testcontainers/testcontainers-python | OK | Approved (already in project) |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

*slopcheck 0.6.1 ran successfully on 2026-05-23 and returned OK for all four packages.*

---

## Architecture Patterns

### System Architecture Diagram

```
[FastAPI lifespan startup]
        │
        ▼
create_async_engine("postgresql+asyncpg://...")
        │  pool_size=5, max_overflow=10
        │
        ▼ stored on
  app.state.engine  ─────────────────────────────────────────────────┐
                                                                      │
[Request handler (future Phase 5/6)]                                  │
        │                                                             │
        ▼ instantiates with engine                                    │
  CacheRepository(engine)                                             │
        │                                                             │
        ├─── find(brand_key, model_key, year)                         │
        │         │                                                   │
        │         ▼                                                   │
        │   async with engine.connect() as conn:                      │
        │     result = await conn.execute(text(SELECT...))            │
        │     return row | None                                        │
        │                                                             │
        └─── insert(brand_key, model_key, year, ...)                  │
                  │                                                   │
                  ▼                                                   │
            async with engine.begin() as conn:                        │
              await conn.execute(text(INSERT ... ON CONFLICT DO NOTHING))
                                                                      │
[FastAPI lifespan shutdown] ◄─────────────────────────────────────────┘
        │
        ▼
  await app.state.engine.dispose()
```

### Recommended Project Structure

New files this phase creates:

```
alembic.ini                                  # Alembic configuration (project root)
alembic/
├── env.py                                   # Async migration runner
├── script.py.mako                           # Migration file template
└── versions/
    └── 0001_create_vehicle_images.py        # First and only migration this phase
src/carpix_images/
├── infrastructure/
│   ├── __init__.py                          # Empty package marker
│   └── cache_repository.py                  # CacheRepository class
└── main.py                                  # Modified: wire pool in lifespan
tests/
├── conftest.py                              # Modified: add postgres_container fixture
└── integration/
    ├── __init__.py                          # Empty package marker
    └── test_cache_repository.py            # Integration tests for DB-01, DB-02, DB-03
```

### Pattern 1: Alembic alembic.ini (mirrors parent project verbatim)

**What:** Root-level config file pointing at the `alembic/` folder.
**When to use:** Always — Alembic requires this.

```ini
# Source: /home/ccastro/Projects/auto-insight-claw/alembic.ini (exact mirror)
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

[logger_alembic]
level = INFO
handlers =
qualname = alembic
```

### Pattern 2: Alembic env.py — async migration runner

**What:** `alembic/env.py` that uses `create_async_engine` + `asyncio.run()` to execute migrations.
**When to use:** Required for any SQLAlchemy async project.

```python
# Source: adapted from /home/ccastro/Projects/auto-insight-claw/alembic/env.py
# [CITED: alembic.sqlalchemy.org/en/latest/cookbook.html]
import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# No target_metadata — we use op.create_table() directly (no ORM autogenerate)
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

### Pattern 3: Migration file — op.create_table() with composite PK

**What:** Alembic migration creating `vehicle_images` table.
**When to use:** First time the table needs to exist.

```python
# Source: pattern from /home/ccastro/Projects/auto-insight-claw/alembic/versions/0001_create_jobs_table.py
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

### Pattern 4: CacheRepository — SQLAlchemy Core text() queries

**What:** Repository class using `AsyncEngine` with `text()` for type-safe, injection-safe SQL.
**When to use:** Any DB operation in Phase 3+.

```python
# Source: SQLAlchemy asyncio docs [CITED: docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html]
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

### Pattern 5: FastAPI lifespan — pool creation and disposal

**What:** Wire `create_async_engine` into the existing lifespan context manager in `main.py`.
**When to use:** Replace the Phase 1 no-op lifespan comment.

```python
# Source: FastAPI lifespan pattern + SQLAlchemy asyncio docs
# [CITED: docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html]
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

**mypy strict note:** `app.state` is `starlette.datastructures.State`, a dynamic namespace. Assigning `app.state.engine = engine` is untyped and will produce `Any` on read. At call sites, use `cast(AsyncEngine, request.app.state.engine)` or pass the engine explicitly into repository constructors at the call site (preferred for testability). [ASSUMED — mypy strict behaviour with Starlette State is based on known limitations, not verified via mypy run in this session.]

### Pattern 6: Integration test — testcontainers + Alembic + CacheRepository

**What:** Run real Postgres via testcontainers, apply migrations via Alembic, test repository.
**When to use:** `tests/integration/test_cache_repository.py`

```python
# Source: adapted from /home/ccastro/Projects/auto-insight-claw/tests/integration/test_archive_integration.py
import os
from collections.abc import Generator

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import create_async_engine
from testcontainers.postgres import PostgresContainer


# In tests/conftest.py:
@pytest.fixture(scope="session")
def postgres_container() -> Generator[str, None, None]:
    with PostgresContainer("postgres:17", driver="asyncpg") as pg:
        url = pg.get_connection_url()
        os.environ["DATABASE_URL"] = url
        yield url


# In tests/integration/test_cache_repository.py:
pytestmark = pytest.mark.usefixtures("postgres_container")


def _alembic_cfg() -> Config:
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])
    return cfg


@pytest.fixture(scope="module", autouse=True)
def run_migrations() -> None:
    command.upgrade(_alembic_cfg(), "head")


@pytest.fixture()
async def engine():
    e = create_async_engine(os.environ["DATABASE_URL"])
    yield e
    await e.dispose()
```

### Anti-Patterns to Avoid

- **Using ORM session instead of Core `text()`:** A cache microservice with one table does not need ORM mapping. `text()` queries are simpler and avoid session state management complexity.
- **Opening a new connection per SQL statement:** Use `async with engine.connect() as conn:` and execute multiple statements on the same connection if needed within a single operation.
- **Not calling `await engine.dispose()`:** Without explicit dispose in the lifespan finally block, asyncpg connections remain open after app shutdown. The async runtime cannot call finalizers in `__del__`.
- **Using `engine.begin()` for read-only queries:** `engine.begin()` opens a write transaction. Use `engine.connect()` for `SELECT`; use `engine.begin()` for `INSERT`/`UPDATE`/`DELETE`.
- **Running `alembic upgrade head` inside a pytest async test function:** Alembic's `command.upgrade()` is synchronous. Call it from a sync fixture (`def run_migrations()`) not an `async def` test or fixture.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Connection pooling | Custom asyncpg pool wrapper | `create_async_engine()` | SQLAlchemy manages pool sizing, overflow, pre-ping, and cleanup automatically |
| Schema migration | Manual `CREATE TABLE` in startup | Alembic `upgrade head` | Alembic tracks applied revisions; idempotent; supports rollback with `downgrade` |
| SQL injection prevention | String interpolation | `text()` with named params | Parameterised queries are the only safe approach; never f-string SQL |
| Duplicate insert handling | `try/except IntegrityError` | `ON CONFLICT DO NOTHING` | Single atomic statement; no race condition between check and insert |

**Key insight:** Alembic + SQLAlchemy Core is the standard Python ecosystem answer to "managed Postgres schema + async queries." Rolling custom solutions for either problem introduces the exact bugs these libraries were built to eliminate.

---

## Common Pitfalls

### Pitfall 1: alembic.ini path resolution in tests

**What goes wrong:** `Config("alembic.ini")` resolves the path relative to the current working directory. If pytest is invoked from a directory other than the project root, Alembic cannot find the file.
**Why it happens:** Alembic uses a bare filename by default; pytest's CWD depends on invocation context.
**How to avoid:** Always run `pytest` from the project root (`/home/ccastro/Projects/carpix`). Alternatively, use `Path(__file__).parent.parent.parent / "alembic.ini"` to resolve the path from the test file's location.
**Warning signs:** `FileNotFoundError: alembic.ini` when running a subset of tests from an IDE.

### Pitfall 2: Driver scheme mismatch between SQLAlchemy and asyncpg

**What goes wrong:** `asyncpg.connect()` requires `postgresql://`, but `settings.database_url` uses `postgresql+asyncpg://` (SQLAlchemy format). Passing the raw DSN to asyncpg causes a connection error.
**Why it happens:** The `+asyncpg` dialect suffix is a SQLAlchemy convention; asyncpg does not recognise it.
**How to avoid:** When using raw asyncpg (e.g., in the health probe), strip the prefix: `dsn.replace("postgresql+asyncpg://", "postgresql://")`. This pattern is already established in `routers/health.py`.
**Warning signs:** `asyncpg.exceptions.InvalidAuthorizationSpecificationError` or connection refused on a known-good DSN.

### Pitfall 3: `app.state.engine` typed as `Any` under mypy strict

**What goes wrong:** `app.state` is `starlette.datastructures.State`, a dynamic dict-backed namespace. Any attribute access returns `Any`, which causes mypy strict to cascade `Any` through callers.
**Why it happens:** Starlette's State class does not use `__slots__` or typed attributes.
**How to avoid:** At call sites that need the engine, use `from typing import cast; engine = cast(AsyncEngine, request.app.state.engine)`. Alternatively, construct `CacheRepository` in the lifespan and store it on `app.state.cache_repository` — then `cast(CacheRepository, ...)` at the call site.
**Warning signs:** mypy reporting `error: Item "Any" of "Union[...]" has no attribute "connect"`.

### Pitfall 4: `asyncio_mode = "auto"` and synchronous Alembic fixtures

**What goes wrong:** pytest-asyncio in `asyncio_mode = "auto"` wraps all `async def` functions. A sync fixture that calls `command.upgrade(...)` is fine. But if the fixture is accidentally declared `async def run_migrations()`, pytest-asyncio makes it a coroutine and Alembic's sync `command.upgrade()` blocks the event loop.
**Why it happens:** Alembic command functions are synchronous and block; they must not run inside an async context.
**How to avoid:** Declare `run_migrations` as `def` (sync), never `async def`. The parent project uses the same pattern.
**Warning signs:** Event loop blocked for >10 seconds during test setup; test timeout.

### Pitfall 5: testcontainers container startup order

**What goes wrong:** If `postgres_container` has `scope="session"` and `run_migrations` has `scope="module"`, but the module fixture runs before the session fixture provides the URL, `os.environ["DATABASE_URL"]` is unset.
**Why it happens:** pytest fixture scoping — session fixtures initialise first, but only if they are depended upon. `autouse=True` module fixtures without explicit dependency on `postgres_container` may run before it.
**How to avoid:** Declare `run_migrations` with explicit dependency on `postgres_container`, OR use `pytestmark = pytest.mark.usefixtures("postgres_container")` at the module level (which forces session fixture first). The parent project uses the `pytestmark` approach.
**Warning signs:** `KeyError: 'DATABASE_URL'` in `_alembic_cfg()`.

---

## Code Examples

### Verified Pattern: Async engine with dispose in lifespan

```python
# Source: SQLAlchemy asyncio docs [CITED: docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html]
from sqlalchemy.ext.asyncio import create_async_engine

engine = create_async_engine("postgresql+asyncpg://user:pass@host/db")
# ... use engine ...
await engine.dispose()  # Required — async cleanup cannot happen in __del__
```

### Verified Pattern: INSERT ON CONFLICT DO NOTHING

```python
# Source: PostgreSQL docs + SQLAlchemy text() [CITED: docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html]
async with engine.begin() as conn:
    await conn.execute(
        text(
            "INSERT INTO vehicle_images (brand_key, model_key, year, ...) "
            "VALUES (:brand_key, :model_key, :year, ...) "
            "ON CONFLICT DO NOTHING"
        ),
        {"brand_key": "toyota", "model_key": "corolla", "year": 2022, ...},
    )
# engine.begin() auto-commits on success, auto-rolls-back on exception
```

### Verified Pattern: SELECT returning optional row

```python
# Source: SQLAlchemy asyncio docs [CITED: docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html]
async with engine.connect() as conn:
    result = await conn.execute(
        text("SELECT * FROM vehicle_images WHERE brand_key = :b AND model_key = :m AND year = :y"),
        {"b": brand_key, "m": model_key, "y": year},
    )
    row = result.fetchone()  # Returns Row | None
```

### Verified Pattern: Alembic migration with composite PK

```python
# Source: parent project /home/ccastro/Projects/auto-insight-claw/alembic/versions/0009_add_job_relationships.py
op.create_table(
    "vehicle_images",
    sa.Column("brand_key", sa.String(), nullable=False),
    sa.Column("model_key", sa.String(), nullable=False),
    sa.Column("year", sa.Integer(), nullable=False),
    ...
    sa.PrimaryKeyConstraint("brand_key", "model_key", "year"),
)
```

### Verified Pattern: testcontainers PostgresContainer with asyncpg driver

```python
# Source: parent project /home/ccastro/Projects/auto-insight-claw/tests/integration/conftest.py
with PostgresContainer("postgres:17", driver="asyncpg") as pg:
    url = pg.get_connection_url()
    # url format: postgresql+asyncpg://test:test@localhost:XXXXX/test
    os.environ["DATABASE_URL"] = url
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| SQLAlchemy ORM with Session for everything | SQLAlchemy Core `text()` for simple microservice repos | SQLAlchemy 2.0 (2023) | Simpler, lower overhead for narrow table access |
| `@app.on_event("startup")` decorator | `@asynccontextmanager` lifespan | FastAPI 0.93 (2023) | `on_event` deprecated; lifespan is the current standard |
| `asyncpg.create_pool()` directly | `create_async_engine("postgresql+asyncpg://...")` | SQLAlchemy 1.4+ | Unified pool management; cleaner dispose semantics |
| Alembic `run_migrations_offline()` | Async `run_migrations_online()` only | Alembic ~1.7+ | Offline mode requires sync engine; async-first projects use online only |

**Deprecated/outdated:**
- `@app.on_event("startup")` / `@app.on_event("shutdown")`: Deprecated since FastAPI 0.93. The existing `lifespan` context manager in `main.py` is already correct.
- SQLAlchemy 1.x: The `2.0` style is the current standard; `execute()` returning a `CursorResult` (not a list) is the new API.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | mypy strict will flag `app.state.engine` as `Any` and require `cast()` at call sites | Common Pitfalls #3, Pattern 5 | If Starlette added typed State in a recent version, `cast()` is unnecessary boilerplate — but harmless |

**If this table is empty:** All claims in this research were verified or cited — no user confirmation needed.

The single assumption (A1) is low-risk: using `cast()` is always safe even if unnecessary.

---

## Open Questions

1. **Alembic `--rev-id` vs auto-generated revision IDs**
   - What we know: Parent project uses manually set `revision = "0001"` (4-digit sequential numbering)
   - What's unclear: Whether `alembic revision` auto-generates a UUID-style ID or honours the sequential naming if passed as `--rev-id 0001`
   - Recommendation: Pass `--rev-id 0001` to `alembic revision` command, or write the migration file manually — the parent project always writes migrations by hand, which is the simpler approach for a project with known schema upfront.

2. **`alembic/versions/` naming convention**
   - What we know: Parent project uses `0001_create_jobs_table.py`
   - What's unclear: Whether Alembic CLI auto-names the file this way or requires `--message` flag
   - Recommendation: Write the migration file manually with the `0001_create_vehicle_images.py` name rather than relying on `alembic revision` output formatting.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker | testcontainers (integration tests) | ✓ | Docker Engine 29.2.1 | — |
| Python 3.12+ | Project requirement | ✓ | 3.13.6 (exceeds minimum) | — |
| asyncpg | DB connection (already in deps) | ✓ | 0.31.0 | — |
| sqlalchemy | async engine pool | ✗ (not yet in project deps) | 2.0.49 available | Add to pyproject.toml as Wave 0 task |
| alembic | schema migrations | ✗ (not yet in project dev deps) | 1.18.4 available | Add to pyproject.toml as Wave 0 task |
| PostgreSQL (local) | — | ✗ | — | testcontainers provides a containerised instance; local psql not needed |

**Missing dependencies with no fallback:** none (sqlalchemy and alembic are available on PyPI and only need to be added to pyproject.toml)

**Missing dependencies with fallback:** none

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 + pytest-asyncio 1.3.0 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (asyncio_mode = "auto") |
| Quick run command | `python -m pytest tests/unit/ -x -q` |
| Full suite command | `python -m pytest tests/ -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DB-01 | Migration creates `vehicle_images` table with composite PK | integration | `python -m pytest tests/integration/test_cache_repository.py::test_migration_creates_table -x` | ❌ Wave 0 |
| DB-02a | `find()` returns row when exists | integration | `python -m pytest tests/integration/test_cache_repository.py::test_find_returns_entry -x` | ❌ Wave 0 |
| DB-02b | `find()` returns None when not exists | integration | `python -m pytest tests/integration/test_cache_repository.py::test_find_returns_none -x` | ❌ Wave 0 |
| DB-02c | `insert()` is idempotent (no error on duplicate) | integration | `python -m pytest tests/integration/test_cache_repository.py::test_insert_idempotent -x` | ❌ Wave 0 |
| DB-03 | Pool created on startup, disposed on shutdown; no leaked connections | integration | `python -m pytest tests/integration/test_cache_repository.py::test_pool_lifecycle -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/unit/ -x -q` (unit tests only; fast)
- **Per wave merge:** `python -m pytest tests/ -x -q` (includes integration; requires Docker)
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/integration/__init__.py` — empty package marker
- [ ] `tests/integration/test_cache_repository.py` — 5 tests covering DB-01, DB-02, DB-03 (written as stubs in Wave 1)
- [ ] `src/carpix_images/infrastructure/__init__.py` — empty package marker
- [ ] `src/carpix_images/infrastructure/cache_repository.py` — stub with `NotImplementedError` (Wave 1)
- [ ] `alembic/` directory + `alembic.ini` + `alembic/env.py` + `alembic/script.py.mako` (Wave 1)
- [ ] `alembic/versions/0001_create_vehicle_images.py` (Wave 1)
- [ ] `sqlalchemy>=2.0` added to `[project].dependencies` (Wave 1)
- [ ] `alembic>=1.18` added to `[project.optional-dependencies].dev` (Wave 1)

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — (internal service, no user auth) |
| V3 Session Management | no | — |
| V4 Access Control | no | — (no user-facing access control) |
| V5 Input Validation | yes | Parameterised `text()` queries with named params — no string interpolation in SQL |
| V6 Cryptography | no | — (no secrets stored in DB) |

### Known Threat Patterns for asyncpg + SQLAlchemy Core

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SQL injection via f-string in `text()` | Tampering | Named parameters in `text()`: `text("... WHERE brand_key = :bk")` with `{"bk": value}` — never f-string |
| Connection pool exhaustion | Denial of Service | SQLAlchemy pool `pool_size` + `max_overflow` limits; lifespan-scoped so pool is shared across requests |
| Sensitive data in DB logs | Information Disclosure | `echo=False` on `create_async_engine()` (the default) — do not set `echo=True` in production |

---

## Sources

### Primary (HIGH confidence)
- SQLAlchemy asyncio docs — `create_async_engine`, `AsyncEngine.dispose()`, `engine.connect()`, `engine.begin()`, `text()` execution
  [CITED: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html]
- Alembic async cookbook — async `env.py` pattern with `asyncio.run()`
  [CITED: https://alembic.sqlalchemy.org/en/latest/cookbook.html]
- Parent project `/home/ccastro/Projects/auto-insight-claw/` — `alembic.ini`, `alembic/env.py`, `alembic/versions/0001_create_jobs_table.py`, `tests/integration/conftest.py`, `tests/integration/test_archive_integration.py` — exact templates
- PyPI registry — versions confirmed via `pip index versions` on 2026-05-23
  [VERIFIED: PyPI registry] — sqlalchemy 2.0.49, alembic 1.18.4, asyncpg 0.31.0, testcontainers 4.14.2

### Secondary (MEDIUM confidence)
- Starlette source `starlette.datastructures.State` — confirmed dynamic `__setattr__`/`__getattr__` via dict; typed access requires `cast()`
  [CITED: starlette package installed in project environment]

### Tertiary (LOW confidence)
- none

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all versions confirmed on PyPI registry; slopcheck OK
- Architecture: HIGH — exact templates exist in parent project; no novel patterns
- Pitfalls: HIGH — pitfalls 1-4 reproduced from parent project history; pitfall 5 from direct inspection of conftest fixture scoping

**Research date:** 2026-05-23
**Valid until:** 2026-07-23 (SQLAlchemy 2.x and Alembic are stable; testcontainers API stable)
