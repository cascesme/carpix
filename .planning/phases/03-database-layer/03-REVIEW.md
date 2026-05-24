---
phase: 03-database-layer
reviewed: 2026-05-24T00:00:00Z
depth: quick
files_reviewed: 8
files_reviewed_list:
  - alembic/env.py
  - alembic/script.py.mako
  - alembic/versions/0001_create_vehicle_images.py
  - src/carpix_images/infrastructure/__init__.py
  - src/carpix_images/infrastructure/cache_repository.py
  - src/carpix_images/main.py
  - tests/conftest.py
  - tests/integration/test_cache_repository.py
findings:
  critical: 2
  warning: 3
  info: 1
  total: 6
status: issues_found
---

# Phase 03: Database Layer — Code Review Report

**Reviewed:** 2026-05-24
**Depth:** quick
**Files Reviewed:** 8
**Status:** issues_found

## Summary

Reviewed the Alembic migration setup, CacheRepository implementation, FastAPI app lifespan,
and integration tests for the database layer. The core repository logic is sound: parameterized
SQL (no injection risk), idempotent inserts via `ON CONFLICT DO NOTHING`, and correct async
context manager usage in `find()` and `insert()`. The migration schema is reasonable.

Two blockers exist: the Alembic `env.py` leaks the SQLAlchemy engine pool on any connection
error (missing `try/finally`), and the integration test `run_migrations` fixture has an
undeclared dependency on `postgres_container` that makes fixture ordering unreliable in CI.
Three warnings round out the set.

---

## Critical Issues

### CR-01: Engine pool leaked when DB is unreachable during migrations

**File:** `alembic/env.py:25-29`
**Issue:** `run_async_migrations()` creates an engine on line 26 and calls `await engine.dispose()` on line 29. If `engine.begin()` raises (e.g., DB is unreachable, bad credentials), the exception propagates and `engine.dispose()` is never called. This leaks the connection pool — a real risk in CI where the DB may not be ready, leaving dangling asyncpg connections that can exhaust the pool or hang the process.

```python
# Current (leaks engine on exception)
async def run_async_migrations() -> None:
    engine = create_async_engine(_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(do_run_migrations)
    await engine.dispose()          # never reached if engine.begin() raises

# Fix: always dispose
async def run_async_migrations() -> None:
    engine = create_async_engine(_DATABASE_URL)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(do_run_migrations)
    finally:
        await engine.dispose()
```

---

### CR-02: `run_migrations` fixture has an undeclared dependency on `postgres_container`, making CI ordering unreliable

**File:** `tests/integration/test_cache_repository.py:58-60`
**Issue:** The `run_migrations` fixture (module-scoped, autouse) calls `_alembic_cfg()` which reads `os.environ["DATABASE_URL"]`. That env var is set to the testcontainer URL only when `postgres_container` runs. However, `run_migrations` never declares `postgres_container` as a parameter, so pytest has no fixture graph edge between them.

`pytestmark = pytest.mark.usefixtures("postgres_container")` (line 22) applies `postgres_container` to *test functions*, not to fixtures. pytest does not guarantee that `postgres_container` executes before the autouse module fixture `run_migrations`. On a clean environment where `DATABASE_URL` is not pre-set, the fallback from `conftest.py` (`postgresql+asyncpg://user:pass@localhost:5432/testdb`) is used, and the migration attempt connects to a non-existent local Postgres — failing the entire test module.

The same undeclared dependency exists in the `engine` fixture (line 64), which also reads `os.environ["DATABASE_URL"]` without declaring `postgres_container`.

```python
# Fix: declare the dependency explicitly in both fixtures
@pytest.fixture(scope="module", autouse=True)
def run_migrations(postgres_container: str) -> None:   # <-- add parameter
    command.upgrade(_alembic_cfg(), "head")

@pytest.fixture()
async def engine(postgres_container: str) -> AsyncGenerator[AsyncEngine, None]:
    e = create_async_engine(os.environ["DATABASE_URL"])
    yield e
    await e.dispose()
```

---

## Warnings

### WR-01: `_DATABASE_URL` captured at module import time in `env.py`

**File:** `alembic/env.py:16`
**Issue:** `_DATABASE_URL = os.environ["DATABASE_URL"]` executes at module level when `env.py` is first imported. Because Alembic re-executes `env.py` in its own script context on each `command.upgrade()` call, this works at runtime. However, it raises `KeyError` in any context where `DATABASE_URL` is not set before the Alembic command runs (e.g., a bare `import alembic.env` in tests or tooling). The value should be read lazily inside `run_async_migrations()`, not captured at import time.

```python
# Fix: read inside the function
async def run_async_migrations() -> None:
    url = os.environ["DATABASE_URL"]      # <-- read here
    engine = create_async_engine(url)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(do_run_migrations)
    finally:
        await engine.dispose()
```

---

### WR-02: `env.py` has no offline migration mode guard

**File:** `alembic/env.py:36`
**Issue:** The standard Alembic `env.py` pattern guards execution with `if context.is_offline_mode()` / `else`. This file calls `run_migrations_online()` unconditionally at module level and has no offline branch. Running `alembic upgrade head --sql` (offline SQL generation) will instead attempt a live DB connection and fail. This breaks a common operational workflow for generating migration SQL to review before applying.

```python
# Fix: add the standard guard
if context.is_offline_mode():
    # generate SQL without a live connection
    context.configure(
        url=_DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    asyncio.run(run_async_migrations())
```

---

### WR-03: `engine` fixture has incorrect return type annotation

**File:** `tests/integration/test_cache_repository.py:64`
**Issue:** The fixture is declared `async def engine() -> AsyncEngine` but it uses `yield`, making it an async generator. The correct return annotation is `AsyncGenerator[AsyncEngine, None]`. The `# type: ignore[override]` and `# type: ignore[misc]` comments suppress the mypy errors rather than fixing them. With `mypy --strict` this would be a hard error without the ignores; the ignores mask a real annotation mistake.

```python
# Fix: correct annotation
from collections.abc import AsyncGenerator

@pytest.fixture()
async def engine(postgres_container: str) -> AsyncGenerator[AsyncEngine, None]:
    e = create_async_engine(os.environ["DATABASE_URL"])
    yield e
    await e.dispose()
```

---

## Info

### IN-01: `ON CONFLICT DO NOTHING` lacks an explicit conflict target

**File:** `src/carpix_images/infrastructure/cache_repository.py:69`
**Issue:** `ON CONFLICT DO NOTHING` without specifying the conflict target `(brand_key, model_key, year)` suppresses conflicts from *any* unique constraint on the table, not just the primary key. This is not currently incorrect (only one unique constraint exists), but it is fragile: adding a second unique index in a future migration would silently suppress conflicts on that new constraint too. Naming the target makes intent explicit and avoids surprises.

```sql
-- Fix
ON CONFLICT (brand_key, model_key, year) DO NOTHING
```

---

_Reviewed: 2026-05-24_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: quick_
