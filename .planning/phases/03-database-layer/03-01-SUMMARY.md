---
phase: 03-database-layer
plan: "01"
subsystem: database
tags: [tdd, red-baseline, sqlalchemy, alembic, infrastructure, integration-tests]
dependency_graph:
  requires: []
  provides:
    - CacheRepository stub (infrastructure package)
    - 5 RED integration tests (DB-01, DB-02, DB-03)
    - sqlalchemy>=2.0 in production deps
    - alembic>=1.18 in dev deps
  affects:
    - pyproject.toml
    - tests/integration/
    - src/carpix_images/infrastructure/
tech_stack:
  added:
    - sqlalchemy==2.0.49 (production dep — async engine pool + text() queries)
    - alembic==1.18.4 (dev dep — schema migrations; used in Wave 2)
  patterns:
    - CacheEntry dataclass with 7 fields matching vehicle_images table columns
    - CacheRepository stub with NotImplementedError on find() and insert()
    - Integration tests using pytestmark + usefixtures("postgres_container") module-level marker
    - sync run_migrations fixture (scope="module", autouse=True) — Alembic is sync, must not run in async context
key_files:
  created:
    - pyproject.toml (modified — sqlalchemy + alembic deps + mypy overrides)
    - src/carpix_images/infrastructure/__init__.py
    - src/carpix_images/infrastructure/cache_repository.py
    - tests/integration/test_cache_repository.py
  modified: []
decisions:
  - SQLAlchemy Core text() queries only (no ORM) — cache microservice with one table does not need ORM mapping
  - run_migrations as sync def — Alembic command.upgrade() is sync and must not block the event loop
  - postgres_container fixture deferred to Wave 2 — Wave 1 only establishes RED baseline
metrics:
  duration: "2 minutes"
  completed: "2026-05-23"
  tasks_completed: 2
  tasks_total: 2
  files_created: 3
  files_modified: 1
---

# Phase 03 Plan 01: Database Layer RED Baseline Summary

**One-liner:** TDD RED phase — CacheRepository stub with NotImplementedError + 5 failing integration tests defining the DB-01/DB-02/DB-03 behavioral contract.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add sqlalchemy + alembic deps and mypy overrides to pyproject.toml | c39385c | pyproject.toml |
| 2 | Scaffold infrastructure package + CacheRepository stub + 5 RED integration tests | c5e9c19 | infrastructure/__init__.py, cache_repository.py, test_cache_repository.py |

## What Was Built

### pyproject.toml Changes

- Added `sqlalchemy>=2.0` to `[project].dependencies` (production dep — Wave 2 uses `create_async_engine`)
- Added `alembic>=1.18` to `[project.optional-dependencies].dev` (Wave 2 uses `command.upgrade`)
- Added two new `[[tool.mypy.overrides]]` blocks: `sqlalchemy.*` and `alembic.*` both with `ignore_missing_imports = true`
- `uv sync --extra dev` resolved: sqlalchemy==2.0.49, alembic==1.18.4

### Infrastructure Package

- `src/carpix_images/infrastructure/__init__.py`: empty package marker
- `src/carpix_images/infrastructure/cache_repository.py`:
  - `CacheEntry` dataclass with 7 fields: brand_key, model_key, year, local_path, source_url, file_title, cached_at
  - `CacheRepository.__init__(engine: AsyncEngine)` stores `self._engine`
  - `find()` raises `NotImplementedError` (stub)
  - `insert()` raises `NotImplementedError` (stub)
  - ruff clean + mypy --strict clean

### Integration Tests (RED Gate)

`tests/integration/test_cache_repository.py`:

- `pytestmark = pytest.mark.usefixtures("postgres_container")` at module level
- Helper functions: `_alembic_cfg()`, `_asyncpg_url()`, `async _table_exists()`
- Fixtures: `run_migrations` (sync, scope="module", autouse=True), `engine` (async), `repo` (sync)
- 5 tests: `test_migration_creates_table` (sync), `test_find_returns_entry` (async), `test_find_returns_none` (async), `test_insert_idempotent` (async), `test_pool_lifecycle` (async)

## Verification Results

### RED Gate

```
uv run pytest tests/integration/ -q
5 errors in 0.48s  (0 passed, 5 ERROR — RED confirmed)
```

Failure reasons (all correct for Wave 1):
1. `alembic.ini` does not exist (Wave 2 creates it)
2. `postgres_container` fixture missing (Wave 2 adds it to tests/conftest.py)
3. `CacheRepository.find()` and `insert()` raise `NotImplementedError`

### Unit Tests Remain Green

```
uv run pytest tests/unit/ -q
16 passed in 0.39s
```

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

| File | Description | Intentional? |
|------|-------------|--------------|
| `src/carpix_images/infrastructure/cache_repository.py` | `find()` and `insert()` raise `NotImplementedError` | Yes — Wave 1 RED baseline; Wave 2 (plan 03-02) implements these methods |

These stubs are the explicit goal of this plan. Wave 2 will implement both methods against real Postgres.

## TDD Gate Compliance

- RED gate: `test(03-01): ...` commit c5e9c19 exists — 5 integration tests written before any implementation
- GREEN gate: Deferred to Wave 2 (plan 03-02) — implementation is Wave 2's responsibility
- REFACTOR gate: N/A for Wave 1

## Self-Check: PASSED

- [x] `src/carpix_images/infrastructure/__init__.py` exists (empty, 0 bytes)
- [x] `src/carpix_images/infrastructure/cache_repository.py` exists (CacheEntry + CacheRepository stub)
- [x] `tests/integration/test_cache_repository.py` exists (5 tests)
- [x] Commit c39385c exists (pyproject.toml)
- [x] Commit c5e9c19 exists (infrastructure + tests)
- [x] 0 integration tests pass (RED confirmed)
- [x] 16 unit tests pass (no regression)
