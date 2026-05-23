---
phase: 03-database-layer
plan: "02"
subsystem: database
tags: [tdd, green-implementation, sqlalchemy, alembic, testcontainers, integration-tests]
dependency_graph:
  requires:
    - 03-01 (CacheRepository stub + 5 RED integration tests)
  provides:
    - Alembic migration creating vehicle_images table with composite PK
    - CacheRepository.find() and insert() real implementations
    - FastAPI lifespan wiring AsyncEngine pool
    - postgres_container session-scoped testcontainers fixture
    - 5 GREEN integration tests (DB-01, DB-02, DB-03)
  affects:
    - alembic.ini
    - alembic/env.py
    - alembic/script.py.mako
    - alembic/versions/0001_create_vehicle_images.py
    - src/carpix_images/infrastructure/cache_repository.py
    - src/carpix_images/main.py
    - tests/conftest.py
    - tests/integration/test_cache_repository.py
    - uv.lock
tech_stack:
  added:
    - Alembic async migration runner (asyncio.run + create_async_engine in env.py)
    - testcontainers[postgres]>=4.14.2 (PostgresContainer("postgres:17", driver="asyncpg"))
  patterns:
    - SQLAlchemy Core text() named params for SQL injection prevention (T-03-03)
    - engine.connect() for SELECT, engine.begin() for INSERT/auto-commit
    - FastAPI lifespan pool: create on startup → app.state.engine → dispose in finally
    - Alembic env.py: target_metadata=None (no ORM), _DATABASE_URL=os.environ["DATABASE_URL"]
    - postgres_container scope="session": one container per full test run
key_files:
  created:
    - alembic.ini
    - alembic/env.py
    - alembic/script.py.mako
    - alembic/versions/0001_create_vehicle_images.py
  modified:
    - src/carpix_images/infrastructure/cache_repository.py (stub → real implementation)
    - src/carpix_images/main.py (no-op lifespan → AsyncEngine pool wiring)
    - tests/conftest.py (added postgres_container fixture)
    - tests/integration/test_cache_repository.py (import sort fix by ruff --fix)
    - uv.lock (synced dev deps)
decisions:
  - engine.connect() for read path (no transaction overhead), engine.begin() for write path (auto-commit/rollback)
  - text() named params only — no f-string SQL anywhere (ASVS V5, T-03-03 mitigated)
  - target_metadata=None in env.py — no ORM autogenerate, migrations use op.create_table() directly
  - echo=False not passed explicitly — SQLAlchemy default prevents SQL+params appearing in logs (T-03-04 accepted)
  - AsyncEngine stored on app.state.engine — single pool shared across requests, not per-request (T-03-05 mitigated)
metrics:
  duration: "~10 minutes"
  completed: "2026-05-23"
  tasks_completed: 2
  tasks_total: 2
  files_created: 4
  files_modified: 5
---

# Phase 03 Plan 02: Database Layer GREEN Implementation Summary

**One-liner:** Alembic async migration + CacheRepository text() queries + FastAPI lifespan pool wiring — all 5 integration tests GREEN against a real Postgres container.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Alembic configuration — alembic.ini, env.py, script.py.mako, migration 0001 | 689f21b | alembic.ini, alembic/env.py, alembic/script.py.mako, alembic/versions/0001_create_vehicle_images.py |
| 2 | Implement CacheRepository + wire lifespan pool + add testcontainers fixture | 9e585ae | cache_repository.py, main.py, tests/conftest.py, uv.lock |

## What Was Built

### Alembic Configuration

- `alembic.ini`: project root; `script_location = alembic`; placeholder URL overridden at runtime by `env.py` reading `$DATABASE_URL`
- `alembic/env.py`: async migration runner — `_DATABASE_URL = os.environ["DATABASE_URL"]`, `target_metadata = None` (no ORM), `asyncio.run(run_async_migrations())` at module level
- `alembic/script.py.mako`: standard Alembic migration template (verbatim copy)
- `alembic/versions/0001_create_vehicle_images.py`: creates `vehicle_images` table with 7 columns and composite PK `(brand_key, model_key, year)` + `cached_at` with `server_default=sa.func.now()`

### CacheRepository Implementation

`src/carpix_images/infrastructure/cache_repository.py`:
- `find()`: `engine.connect()` (read path) → `text()` SELECT with named params → `result.fetchone()` inside context → returns `CacheEntry` or `None`
- `insert()`: `engine.begin()` (write path, auto-commit) → `text()` INSERT … `ON CONFLICT DO NOTHING` → no return

SQL injection prevention: all SQL uses `text()` with `:named_params` — no f-strings, no string interpolation (STRIDE T-03-03 fully mitigated).

### FastAPI Lifespan Pool

`src/carpix_images/main.py`:
- `lifespan()`: `create_async_engine(settings.database_url)` on startup → `app.state.engine = engine` → `try/yield/finally` → `await engine.dispose()` on shutdown
- No `echo=True` — SQL with parameter values never appears in logs (T-03-04)
- Default `pool_size=5`, `max_overflow=10` — adequate for internal microservice traffic (T-03-05)

### Testcontainers Fixture

`tests/conftest.py`:
- `postgres_container` fixture: `scope="session"`, `PostgresContainer("postgres:17", driver="asyncpg")` → sets `os.environ["DATABASE_URL"]` to real container URL → yields URL string
- Existing `os.environ.setdefault(...)` guards remain (protect unit tests without Docker)

## Verification Results

### GREEN Gate

```
uv run pytest -q
.....                                                                    [100%]
5 passed in 3.55s  (integration tests — real Postgres container)

................                                                         [100%]
16 passed in 0.43s  (unit tests — no Docker)
```

### Linting & Type Checks

```
uv run ruff check src/ tests/ alembic/
All checks passed!

uv run mypy src/carpix_images/ --strict
Success: no issues found in 11 source files
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] ruff E501 line too long in cache_repository.py**
- **Found during:** Task 2 verification
- **Issue:** SQL VALUES clause string exceeded 88 chars on one line
- **Fix:** Split the VALUES string literal across two lines to fit within 88 chars
- **Files modified:** `src/carpix_images/infrastructure/cache_repository.py`
- **Commit:** 9e585ae (included in task commit)

**2. [Rule 1 - Bug] ruff I001 import sort in test_cache_repository.py**
- **Found during:** Task 2 verification
- **Issue:** Import block ordering in test file needed sorting (ruff UP rule)
- **Fix:** `uv run ruff check --fix` applied automatically
- **Files modified:** `tests/integration/test_cache_repository.py`
- **Commit:** 9e585ae (included in task commit)

**3. [Rule 1 - Bug] alembic/versions migration ruff UP035/UP007/I001 violations**
- **Found during:** Task 1 verification
- **Issue:** `from typing import Sequence, Union` (UP035: use collections.abc), `Union[X, None]` (UP007: use X | None), import sort
- **Fix:** `uv run ruff check alembic/ --fix` applied automatically + `type: ignore[attr-defined]` on `from alembic import op`
- **Files modified:** `alembic/versions/0001_create_vehicle_images.py`, `alembic/env.py`
- **Commit:** 689f21b (included in task commit)

## Known Stubs

None — all stubs from Plan 01 are now implemented.

## Threat Surface Scan

No new security-relevant surface introduced beyond what was planned in the threat model:
- T-03-03 (SQL injection): mitigated via `text()` named params — no f-string SQL
- T-03-04 (credential logging): mitigated — no `echo=True` passed to `create_async_engine()`
- T-03-05 (pool exhaustion): mitigated — single lifespan-scoped engine, default pool settings

## TDD Gate Compliance

- RED gate: `test(03-01): ...` commit c5e9c19 (from Plan 01) — 5 failing integration tests written first
- GREEN gate: `feat(03-02): ...` commits 689f21b + 9e585ae — all 5 tests now pass
- REFACTOR gate: N/A — no refactoring needed

## Self-Check: PASSED

- [x] `alembic.ini` exists — `grep -c "script_location = alembic" alembic.ini` returns 1
- [x] `alembic/env.py` exists — `grep -c "target_metadata = None" alembic/env.py` returns 1
- [x] `alembic/script.py.mako` exists (non-empty)
- [x] `alembic/versions/0001_create_vehicle_images.py` exists — `grep -c "PrimaryKeyConstraint" ...` returns 1
- [x] `src/carpix_images/infrastructure/cache_repository.py` — `grep -c "ON CONFLICT DO NOTHING"` returns 1
- [x] `src/carpix_images/main.py` — `grep -c "app.state.engine"` returns 1
- [x] `tests/conftest.py` — `grep -c "postgres_container"` returns 1
- [x] Commit 689f21b exists (Task 1 — Alembic artefacts)
- [x] Commit 9e585ae exists (Task 2 — implementation + fixtures)
- [x] 5 integration tests pass GREEN
- [x] 16 unit tests pass GREEN
- [x] `uv run ruff check src/ tests/ alembic/` exits 0
- [x] `uv run mypy src/carpix_images/ --strict` exits 0
