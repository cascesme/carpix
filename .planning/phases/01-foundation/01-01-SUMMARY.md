---
phase: 01-foundation
plan: 01
subsystem: infra
tags: [uv, fastapi, pytest, mypy, ruff, asyncpg, pydantic-settings, tdd]

# Dependency graph
requires: []
provides:
  - uv-managed src-layout Python package skeleton for carpix-images
  - pyproject.toml with all runtime and dev dependencies pinned via uv.lock
  - ruff/mypy/pytest tool config matching parent project conventions
  - Wave 0 RED test suite (11 failing tests) for NORM-01, API-03, API-05
  - conftest.py with DATABASE_URL env guard before any carpix_images import
affects:
  - 01-02 (Plan 02 implements source modules to turn RED tests GREEN)
  - 01-03 and beyond (all phases depend on this package scaffold)

# Tech tracking
tech-stack:
  added:
    - uv 0.11.16 (package manager and virtual env)
    - fastapi 0.136.1
    - uvicorn[standard] 0.47.0
    - asyncpg 0.31.0
    - pydantic-settings 2.14.1
    - pytest 9.0.3 + pytest-asyncio 1.3.0
    - httpx 0.28.1
    - ruff 0.15.14
    - mypy 2.1.0
    - respx 0.23.1
    - testcontainers[postgres] 4.14.2
  patterns:
    - src-layout package (src/carpix_images/) with hatchling build backend
    - TDD RED baseline — stubs raise NotImplementedError, tests collect but fail
    - conftest.py env guard pattern (os.environ.setdefault before any module import)
    - pytest asyncio_mode=auto (no per-test @pytest.mark.asyncio decorator)

key-files:
  created:
    - pyproject.toml
    - .env.example
    - uv.lock
    - .gitignore
    - src/carpix_images/__init__.py
    - src/carpix_images/domain/__init__.py
    - src/carpix_images/routers/__init__.py
    - src/carpix_images/config.py (stub)
    - src/carpix_images/domain/normalize.py (stub — canonical_key raises NotImplementedError)
    - src/carpix_images/main.py (stub — create_app raises NotImplementedError)
    - src/carpix_images/routers/health.py (stub — asyncpg imported for patch target)
    - tests/__init__.py
    - tests/unit/__init__.py
    - tests/integration/__init__.py
    - tests/conftest.py
    - tests/unit/test_normalize.py
    - tests/unit/test_health.py
  modified: []

key-decisions:
  - "Stubs created in src/carpix_images/ to enable pytest --collect-only success (module-level imports in test files require resolvable names)"
  - "asyncpg imported with # noqa: F401 in health stub to preserve patch target for tests"
  - "DATABASE_URL only in conftest.py (D-06 — no REDIS_URL or other env vars)"
  - "app = create_app() NOT at module level in stub (prevents collection error from NotImplementedError)"

patterns-established:
  - "TDD RED pattern: stubs with raise NotImplementedError allow collection to succeed while keeping tests failing"
  - "conftest.py env guard: os.environ.setdefault(DATABASE_URL) before any carpix_images import"
  - "Three mypy overrides: asyncpg, pydantic_settings, testcontainers (no parent project extras)"

requirements-completed: [NORM-01, API-03, API-05]

# Metrics
duration: 5min
completed: 2026-05-22
---

# Phase 1 Plan 01: Project Scaffold Summary

**uv-managed src-layout FastAPI skeleton with hatchling, 44-package lockfile, and 11-test RED baseline covering NORM-01 / API-03 / API-05**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-05-22T17:12:00Z
- **Completed:** 2026-05-22T17:16:51Z
- **Tasks:** 3 of 3
- **Files modified:** 17

## Accomplishments

- Installed uv 0.11.16 and scaffolded the src-layout package structure for carpix-images
- Authored pyproject.toml with runtime + dev deps, ruff/mypy/pytest config mirroring parent project; generated uv.lock with 44 pinned packages
- Created conftest.py env guard, 11 failing unit tests for NORM-01 / API-03 / API-05 / /docs — RED TDD baseline established

## Task Commits

Each task was committed atomically:

1. **Task 1: Scaffold src-layout package skeleton** - `650deed` (chore)
2. **Task 2: Author pyproject.toml and sync dependencies** - `f80737f` (chore)
3. **Task 3: Write Wave 0 failing test stubs** - `4d76171` (test — TDD RED)

## Files Created/Modified

- `pyproject.toml` - src-layout package config, all deps, ruff/mypy/pytest tool config
- `.env.example` - DATABASE_URL=postgresql+asyncpg:// placeholder (D-06 only)
- `uv.lock` - 44-package deterministic lockfile
- `.gitignore` - Excludes __pycache__, .venv, .env
- `src/carpix_images/__init__.py` - Empty package marker
- `src/carpix_images/domain/__init__.py` - Empty package marker
- `src/carpix_images/routers/__init__.py` - Empty package marker
- `src/carpix_images/config.py` - Stub Settings(BaseSettings) placeholder
- `src/carpix_images/domain/normalize.py` - Stub canonical_key (raises NotImplementedError)
- `src/carpix_images/main.py` - Stub create_app (raises NotImplementedError, no module-level call)
- `src/carpix_images/routers/health.py` - Stub with asyncpg import for patch target
- `tests/__init__.py` - Empty test package marker
- `tests/unit/__init__.py` - Empty test package marker
- `tests/integration/__init__.py` - Empty placeholder for Phase 3+
- `tests/conftest.py` - DATABASE_URL env guard before any carpix_images import
- `tests/unit/test_normalize.py` - 8 tests covering NORM-01 (parametrized + class-based)
- `tests/unit/test_health.py` - 3 tests covering API-03, API-05, /docs

## Decisions Made

- Stubs created in src/carpix_images/ to support module-level test imports while keeping tests RED. This deviates from "no source files in this plan" but is required for collection to succeed — module-level `from carpix_images.main import create_app` fails at collection time without a resolvable module.
- `app = create_app()` removed from stub main.py to prevent NotImplementedError at collection time.
- `asyncpg` kept in health stub with `# noqa: F401` to preserve the patch target `carpix_images.routers.health.asyncpg.connect` that tests rely on.
- Only DATABASE_URL set in conftest.py (D-06 constraint enforced — no REDIS_URL or other parent-project env vars).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Created source module stubs to enable test collection**
- **Found during:** Task 3 (Wave 0 failing test stubs)
- **Issue:** Module-level imports in test files (`from carpix_images.main import create_app`, `from carpix_images.domain.normalize import canonical_key`) caused `ModuleNotFoundError` at collection time. The plan's acceptance criteria requires `pytest --collect-only` to succeed, which contradicts "no source files in this plan" when module-level imports are used.
- **Fix:** Created minimal stub source files (`config.py`, `domain/normalize.py`, `main.py`, `routers/health.py`) with no business logic. Functions raise `NotImplementedError`, imports resolve, and collection succeeds. Tests remain RED.
- **Files modified:** src/carpix_images/config.py, src/carpix_images/domain/normalize.py, src/carpix_images/main.py, src/carpix_images/routers/health.py
- **Verification:** `uv run pytest tests/unit/ --collect-only` exits 0 with 11 tests collected; `uv run pytest tests/unit/` reports 11 failed.
- **Committed in:** 4d76171 (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (Rule 3 - Blocking)
**Impact on plan:** Required for acceptance criteria compliance. No scope creep — stubs contain zero business logic.

## Known Stubs

| File | Line | Reason |
|------|------|--------|
| src/carpix_images/domain/normalize.py | 5 | `canonical_key` raises NotImplementedError — implemented in Plan 02 |
| src/carpix_images/main.py | 6 | `create_app` raises NotImplementedError — implemented in Plan 02 |
| src/carpix_images/config.py | 1-7 | Settings stub with empty database_url default — implemented in Plan 02 |
| src/carpix_images/routers/health.py | 2-5 | No route registered — implemented in Plan 02 |

These stubs are intentional. Plan 02 replaces all stubs with full implementations, turning the 11 RED tests GREEN.

## Issues Encountered

- ruff F401 on `import asyncpg` in health stub — suppressed with `# noqa: F401` since the import is required as the patch target for `carpix_images.routers.health.asyncpg.connect` in test_health.py.

## Next Phase Readiness

- Package scaffold, uv environment, and lockfile are ready for Plan 02 implementation
- 11 RED tests define the exact contract Plan 02 must satisfy
- conftest.py env guard is in place so Plan 02 implementation can be imported safely in tests
- No blockers

---
*Phase: 01-foundation*
*Completed: 2026-05-22*
