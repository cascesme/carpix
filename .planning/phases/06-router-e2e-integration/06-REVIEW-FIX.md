---
phase: 06-router-e2e-integration
fixed_at: 2026-05-24T00:00:00Z
review_path: .planning/phases/06-router-e2e-integration/06-REVIEW.md
iteration: 1
findings_in_scope: 3
fixed: 3
skipped: 0
status: all_fixed
---

# Phase 06: Code Review Fix Report

**Fixed at:** 2026-05-24T00:00:00Z
**Source review:** .planning/phases/06-router-e2e-integration/06-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 3 (CR-01, WR-01, WR-02)
- Fixed: 3
- Skipped: 0

## Fixed Issues

### CR-01: Unhandled httpx.HTTPStatusError from CDN download produces HTTP 500

**Files modified:** `src/carpix_images/services/image_service.py`
**Commit:** 3b267e8
**Applied fix:** Wrapped the CDN `client.get()` and `response.raise_for_status()` calls in a `try/except (httpx.HTTPStatusError, httpx.RequestError)` block that raises `HTTPException(status_code=404)`. Both network errors and non-2xx CDN responses now map to a clean 404, satisfying the "never a 500" contract from CLAUDE.md.

### WR-01: ImageService creates a bare httpx.AsyncClient bypassing the injected client

**Files modified:** `src/carpix_images/services/image_service.py`, `src/carpix_images/main.py`, `tests/unit/test_image_service.py`
**Commit:** ea3ba14
**Applied fix:**
1. Added `http_client: httpx.AsyncClient` parameter to `ImageService.__init__`, stored as `self._http_client`.
2. Removed the `async with httpx.AsyncClient() as client:` block; the CDN download now uses `self._http_client` directly (no context manager, lifecycle managed by lifespan).
3. The error handling from CR-01 was incorporated into this path at the same time (the `try/except` block from CR-01 was preserved and now wraps the `self._http_client.get()` call).
4. Updated `main.py` lifespan to pass `http_client=http_client` to `ImageService(...)`.
5. Updated `tests/unit/test_image_service.py` `_make_service()` factory to pass `http_client=httpx.AsyncClient()` — respx patches at the transport level so existing mock routes continue to be intercepted correctly.

### WR-02: Self-healing re-fetch does not update the stale DB record

**Files modified:** `src/carpix_images/infrastructure/cache_repository.py`
**Commit:** d1d4530
**Applied fix:** Replaced `ON CONFLICT DO NOTHING` with `ON CONFLICT (brand_key, model_key, year) DO UPDATE SET local_path = EXCLUDED.local_path, source_url = EXCLUDED.source_url, file_title = EXCLUDED.file_title, cached_at = now()`. The INSERT path is unchanged (`cached_at` still defaults to `now()` via the column default). On re-fetch after self-healing, the stale DB row is now fully refreshed.

## Skipped Issues

None — all in-scope findings were fixed.

---

**Lint/type/test results after all fixes:**
- `ruff check src/ tests/`: All checks passed
- `mypy --strict src/`: Success, no issues found in 14 source files
- `pytest tests/unit/ -x -q`: 27 passed in 0.49s

**Not fixed (out of scope):**
- IN-01 (file_title empty string for trailing-slash URLs) — excluded per fix scope (Info only)

---

_Fixed: 2026-05-24T00:00:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
