---
phase: 01-foundation
plan: 02
subsystem: api
tags: [fastapi, asyncpg, pydantic-settings, normalize, health, tdd]

# Dependency graph
requires:
  - phase: 01-foundation
    plan: 01
    provides: uv src-layout skeleton, pyproject.toml, 11 RED test baseline
provides:
  - canonical_key normalization (NORM-01) — strips non-alphanumeric, lowercases
  - pydantic-settings Settings with database_url field (D-06 constraint)
  - /health router with asyncpg SELECT 1 probe (API-03, API-05)
  - FastAPI app factory (create_app) and module-level app for uvicorn
affects:
  - 01-03 and beyond (all phases use normalized keys and /health for readiness checks)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - canonical_key verbatim from parent project vehicle_identity.py
    - Settings(BaseSettings) with SettingsConfigDict — module-level singleton
    - asyncpg DSN scheme stripping (postgresql+asyncpg:// -> postgresql://)
    - lifespan async context manager (no-op Phase 1, wired in Phase 3)
    - asynccontextmanager with AsyncGenerator[None, None] return type for mypy strict

key-files:
  created: []
  modified:
    - src/carpix_images/domain/normalize.py
    - src/carpix_images/config.py
    - src/carpix_images/routers/health.py
    - src/carpix_images/main.py

key-decisions:
  - "AsyncGenerator imported from collections.abc (not typing) per ruff UP035 rule for Python 3.12 target"
  - "asyncpg timeout=3 confirmed valid kwarg via inspect.signature — kept for health probe"
  - "lifespan app arg typed as FastAPI with AsyncGenerator[None, None] return for mypy strict compliance"
  - "ruff format applied to test files (line-length alignment) as part of quality gate"

patterns-established:
  - "canonical_key: re.sub(r'[^a-z0-9]', '', value.lower()) — verbatim from parent project"
  - "DSN scheme stripping before asyncpg.connect: replace('postgresql+asyncpg://', 'postgresql://')"
  - "Health endpoint always returns status=ok; db field reflects probe only"
  - "collections.abc.AsyncGenerator for async generator type hints (UP035)"

requirements-completed: [NORM-01, API-03, API-05]

# Metrics
duration: 10min
completed: 2026-05-22
---

# Phase 1 Plan 02: Source Module Implementation Summary

**canonical_key normalization, pydantic-settings config, asyncpg /health probe, and FastAPI app factory turn all 11 RED tests GREEN with ruff+mypy clean**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-05-22T17:20:00Z
- **Completed:** 2026-05-22T17:30:00Z
- **Tasks:** 3 of 3
- **Files modified:** 4

## Accomplishments

- Implemented `canonical_key` verbatim from parent project — 8 NORM-01 parametrized + class-based tests pass
- Implemented `Settings(BaseSettings)` with single `database_url` field satisfying D-06 constraint; module-level singleton confirms env-at-import-time pattern
- Implemented `/health` router with asyncpg SELECT 1 probe (timeout=3) and try/except db_status logic; app factory with no-op lifespan; all 11 tests GREEN, ruff+mypy zero errors

## Task Commits

Each task was committed atomically:

1. **Task 1: canonical_key + Settings config** - `d95b763` (feat)
2. **Task 2: /health router + app factory** - `507ba5e` (feat)
3. **Task 3: Quality gate — ruff, mypy, format, full suite** - `f0f64f2` (test)

## Files Created/Modified

- `src/carpix_images/domain/normalize.py` - canonical_key implementation (from __future__ annotations, re.sub pattern)
- `src/carpix_images/config.py` - Settings(BaseSettings) with SettingsConfigDict and database_url field; module-level settings singleton
- `src/carpix_images/routers/health.py` - /health GET endpoint with asyncpg connect probe, DSN scheme stripping, try/except pattern
- `src/carpix_images/main.py` - lifespan no-op, create_app factory, module-level app = create_app()

## Decisions Made

- Imported `AsyncGenerator` from `collections.abc` rather than `typing` — ruff UP035 rule requires this for Python 3.12 target
- Verified `timeout` kwarg exists in asyncpg 0.31.0 `asyncpg.connect` signature before including it
- Applied `ruff format` to test files reformatted by the formatter (trailing whitespace in parametrize blocks) — zero test logic changed

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed UP035 import violation in main.py**
- **Found during:** Task 3 (Quality gate — ruff check)
- **Issue:** `from typing import AsyncGenerator` flagged as UP035 by ruff; Python 3.12 target requires `collections.abc.AsyncGenerator`
- **Fix:** Changed import to `from collections.abc import AsyncGenerator`
- **Files modified:** src/carpix_images/main.py
- **Verification:** `uv run ruff check src/` exits 0
- **Committed in:** f0f64f2 (Task 3 commit)

**2. [Rule 1 - Bug] Applied ruff format to test files**
- **Found during:** Task 3 (Quality gate — ruff format --check)
- **Issue:** `tests/unit/test_health.py` and `tests/unit/test_normalize.py` had minor formatting drift (trailing whitespace in parametrize tuples)
- **Fix:** `uv run ruff format src/ tests/` — 2 files reformatted, no logic changes
- **Files modified:** tests/unit/test_health.py, tests/unit/test_normalize.py
- **Verification:** `uv run ruff format --check src/ tests/` exits 0 with "13 files already formatted"
- **Committed in:** f0f64f2 (Task 3 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 — ruff lint/format)
**Impact on plan:** Required for quality gate compliance. Zero logic changes — formatting and import modernization only.

## Issues Encountered

- None beyond the two ruff violations auto-fixed above.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- All 11 unit tests GREEN; ruff+mypy zero errors; uvicorn import verified
- `/health` endpoint ready for integration testing with a real Postgres container (Phase 3)
- canonical_key available for image cache routing (Phase 2+)
- No blockers

---
*Phase: 01-foundation*
*Completed: 2026-05-22*
