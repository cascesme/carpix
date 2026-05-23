---
phase: 02-storage-layer
plan: 01
subsystem: testing
tags: [pytest, fastapi, pathlib, anyio, tdd, red-baseline]

# Dependency graph
requires:
  - phase: 01-foundation
    provides: conftest.py DATABASE_URL guard, test infrastructure, carpix_images package layout
provides:
  - StorageService stub class (raises NotImplementedError) importable from carpix_images.services.storage
  - 5 failing unit tests covering STORE-01 and STORE-02 (RED baseline)
  - IMAGES_DIR env guard in tests/conftest.py
affects: [02-storage-layer Plan 02 (GREEN implementation)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "TDD RED baseline: stub raises NotImplementedError, tests imported with correct signatures"
    - "services/ package follows domain/ convention: empty __init__.py"
    - "from __future__ import annotations header on all new modules"
    - "top-level FileResponse import in test file (ruff I001 compliance)"

key-files:
  created:
    - src/carpix_images/services/__init__.py
    - src/carpix_images/services/storage.py
    - tests/unit/test_storage.py
  modified:
    - tests/conftest.py

key-decisions:
  - "anyio not imported in stub — ruff F401 flags unused imports even in stubs; removed to keep ruff clean"
  - "Method signatures wrapped to 88-char limit per ruff E501"
  - "FileResponse imported at top level in test_storage.py for ruff I001 compliance (not inside method)"

patterns-established:
  - "StorageService stub: all methods raise NotImplementedError; __init__ can execute (resolve base_dir)"
  - "PYTHONPATH=worktree/src required for worktree-isolated test runs (editable install points to main checkout)"

requirements-completed:
  - STORE-01
  - STORE-02

# Metrics
duration: 2min
completed: 2026-05-23
---

# Phase 02 Plan 01: Storage Layer RED Baseline Summary

**StorageService stub with NotImplementedError bodies and 5 failing unit tests establishing the TDD RED baseline for STORE-01 (save) and STORE-02 (path traversal guard)**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-05-23T07:50:51Z
- **Completed:** 2026-05-23T07:53:29Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Created `src/carpix_images/services/__init__.py` (empty package marker) and `src/carpix_images/services/storage.py` (StorageService stub, all methods raise NotImplementedError)
- Created `tests/unit/test_storage.py` with 5 unit tests: 3 for `save()` (correct path, intermediate dirs, idempotency) and 2 for `file_response()` (valid path returns FileResponse, traversal raises ValueError)
- All 5 new tests FAIL with NotImplementedError (RED); 11 pre-existing tests unaffected and still GREEN (16 total collected)
- Added `IMAGES_DIR` env guard to `tests/conftest.py` alongside existing `DATABASE_URL` guard
- ruff and mypy clean on all new/modified files

## Task Commits

1. **Task 1: Create services package + StorageService stub** - `8bbce77` (test)
2. **Task 2: Write 5 failing unit tests for StorageService** - `3b673b7` (test)

## Files Created/Modified

- `src/carpix_images/services/__init__.py` - Empty package marker enabling `carpix_images.services` imports
- `src/carpix_images/services/storage.py` - StorageService class stub: __init__ resolves base_dir, all other methods raise NotImplementedError
- `tests/unit/test_storage.py` - 5 failing unit tests for STORE-01 and STORE-02 with class-based structure
- `tests/conftest.py` - Added `os.environ.setdefault("IMAGES_DIR", "/tmp/carpix_test_images")`

## Decisions Made

- **anyio omitted from stub imports:** The stub's methods all raise NotImplementedError so anyio would be unused. ruff F401 flags unused imports; removed to keep ruff clean. Plan 02 will add anyio back when implementing the actual `save()` method.
- **Method signatures wrapped to 88-char limit:** ruff E501 enforced; long signatures split across two lines using standard continuation style.
- **FileResponse imported at top level in test file:** Plan Task 2 explicitly required top-level import to follow ruff I001 import ordering rules (not inside the test method as shown in PATTERNS.md).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed unused anyio import and fixed line-too-long in stub**
- **Found during:** Task 1 (Create services package + StorageService stub)
- **Issue:** Initial stub included `import anyio` (unused in NotImplementedError stub), triggering ruff F401. `async def save(...)` signature exceeded 88 chars, triggering ruff E501.
- **Fix:** Removed `import anyio`; wrapped long method signatures to two lines with continuation indent.
- **Files modified:** `src/carpix_images/services/storage.py`
- **Verification:** `python3 -m ruff check src/carpix_images/services/` exits 0
- **Committed in:** `8bbce77` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - ruff compliance)
**Impact on plan:** Cosmetic fix; stub behavior (all methods raise NotImplementedError) unchanged. Plan 02 will add anyio import back when implementing save().

## Issues Encountered

None. Plan executed as specified with one minor auto-fix for ruff compliance.

## Known Stubs

The following stubs are intentional and expected to fail (this is the RED baseline):

| File | Method | Stub Type | Resolved In |
|------|--------|-----------|-------------|
| `src/carpix_images/services/storage.py` | `save()` | `raise NotImplementedError` | Plan 02 (GREEN) |
| `src/carpix_images/services/storage.py` | `_validated_path()` | `raise NotImplementedError` | Plan 02 (GREEN) |
| `src/carpix_images/services/storage.py` | `file_response()` | `raise NotImplementedError` | Plan 02 (GREEN) |

These stubs are intentional and are the goal of Plan 01. Plan 02 (Wave 2) will implement them.

## Next Phase Readiness

- Plan 02 (Wave 2) can now implement StorageService against a clear RED test suite
- All 5 tests define the exact contract Plan 02 must satisfy
- No pre-existing tests broken; test infrastructure intact

## Self-Check: PASSED

- `src/carpix_images/services/__init__.py` - FOUND
- `src/carpix_images/services/storage.py` - FOUND
- `tests/unit/test_storage.py` - FOUND
- Commit `8bbce77` - FOUND (Task 1)
- Commit `3b673b7` - FOUND (Task 2)
- 5 tests collected and failing (NotImplementedError) - VERIFIED
- 16 total tests collected (11 existing + 5 new) - VERIFIED
- ruff clean on all new files - VERIFIED
- mypy clean on all new files - VERIFIED

---
*Phase: 02-storage-layer*
*Completed: 2026-05-23*
