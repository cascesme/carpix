---
phase: 06-router-e2e-integration
reviewed: 2026-05-24T00:00:00Z
depth: quick
files_reviewed: 5
files_reviewed_list:
  - src/carpix_images/main.py
  - src/carpix_images/routers/images.py
  - src/carpix_images/services/image_service.py
  - tests/integration/test_images_router.py
  - tests/unit/test_image_service.py
findings:
  critical: 1
  warning: 2
  info: 1
  total: 4
status: issues_found
---

# Phase 06: Code Review Report

**Reviewed:** 2026-05-24T00:00:00Z
**Depth:** quick
**Files Reviewed:** 5
**Status:** issues_found

## Summary

Five files were reviewed: the application entry point, the images router, the image service, and both the unit and integration test suites. The code is well-structured and the concurrency logic (per-key asyncio locks) is correct. One BLOCKER was found: an unhandled exception from a CDN HTTP error response that violates the stated contract of "never a 500." Two warnings were found around a bare `httpx.AsyncClient` created inside the service bypassing the injected client, and a DB `INSERT` not updating stale records on self-heal. One info item covers a degenerate file_title extraction edge case.

---

## Critical Issues

### CR-01: Unhandled `httpx.HTTPStatusError` from CDN download produces HTTP 500

**File:** `src/carpix_images/services/image_service.py:52-55`

**Issue:** `response.raise_for_status()` on line 54 is outside any `try/except` block. If the Wikimedia CDN returns a non-2xx response (429 rate-limit, 404 not found, 5xx server error), `httpx.HTTPStatusError` propagates uncaught through `get_or_fetch` and through the router, causing FastAPI to return a 500 Internal Server Error to the caller. CLAUDE.md explicitly requires: "Error handling: Extraction failures always 404, never 500."

The same applies to the `await client.get(url, ...)` call on line 53 — a network error (`httpx.RequestError`) also propagates as a 500.

**Fix:**
```python
async with httpx.AsyncClient() as client:
    try:
        response = await client.get(url, timeout=httpx.Timeout(30.0))
        response.raise_for_status()
    except (httpx.HTTPStatusError, httpx.RequestError):
        raise HTTPException(
            status_code=404,
            detail="No image found for this vehicle",
        )
    image_bytes: bytes = response.content
```

---

## Warnings

### WR-01: `ImageService` creates a bare `httpx.AsyncClient` bypassing the injected client

**File:** `src/carpix_images/services/image_service.py:52`

**Issue:** The service already receives an `httpx.AsyncClient` indirectly (through `WikimediaClient`), and `main.py` creates a shared `http_client` in lifespan for exactly this purpose. On the CDN download path, `image_service.py` instantiates a new `httpx.AsyncClient()` inline — bypassing the application-managed client. This means:
- The CDN download client does not share connection pools, timeout config, or any custom transport set up at app bootstrap.
- Under load, this spawns a new client (and TCP connection pool) per request rather than reusing pooled connections.
- In tests, `respx_mock` does intercept this client (because respx patches at the transport level globally), so tests pass, but the architecture is inconsistent with the dependency injection pattern used everywhere else.

**Fix:** Either inject a second `httpx.AsyncClient` explicitly for CDN downloads, or pass the existing app-level client to `ImageService` and use it directly:

```python
class ImageService:
    def __init__(
        self,
        storage: StorageService,
        repo: CacheRepository,
        wikimedia: WikimediaClient,
        http_client: httpx.AsyncClient,   # injected
    ) -> None:
        ...
        self._http_client = http_client

    # in get_or_fetch:
    response = await self._http_client.get(url, timeout=httpx.Timeout(30.0))
```

### WR-02: Self-healing re-fetch does not update the stale DB record

**File:** `src/carpix_images/services/image_service.py:38-69`

**Issue:** When the self-healing path fires (DB hit but file missing, lines 39-43), the code falls through to the full re-fetch path (lines 45-69). At line 61 it calls `self._repo.insert(...)` with `ON CONFLICT DO NOTHING`. This means the stale row in `vehicle_images` (pointing to the now-missing file path) is never updated. The `local_path` and `source_url` columns in the DB may reflect stale data if the re-fetch produces a different URL (e.g., Wikimedia file was renamed or CDN path changed). The `cached_at` timestamp is also permanently stale.

**Fix:** Replace `ON CONFLICT DO NOTHING` with an upsert that refreshes stale fields, or delete-then-insert, or add a dedicated `update` method:

```sql
INSERT INTO vehicle_images
  (brand_key, model_key, year, local_path, source_url, file_title)
VALUES
  (:brand_key, :model_key, :year, :local_path, :source_url, :file_title)
ON CONFLICT (brand_key, model_key, year) DO UPDATE SET
  local_path  = EXCLUDED.local_path,
  source_url  = EXCLUDED.source_url,
  file_title  = EXCLUDED.file_title,
  cached_at   = now()
```

---

## Info

### IN-01: `file_title` extracted by `rsplit("/", 1)` yields empty string for trailing-slash URLs

**File:** `src/carpix_images/services/image_service.py:60`

**Issue:** `url.rsplit("/", 1)[-1]` yields an empty string `""` if the CDN URL ends with a slash (e.g., `"https://upload.wikimedia.org/thumb/a/ab/"`). While this is an unlikely edge case for Wikimedia CDN thumbnail URLs, an empty `file_title` stored in the DB is a latent data quality issue.

**Fix:** Add a guard or use `Path(url).name` (after stripping query strings):

```python
from urllib.parse import urlsplit
file_title = urlsplit(url).path.rsplit("/", 1)[-1] or "image.jpg"
```

---

_Reviewed: 2026-05-24T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: quick_
