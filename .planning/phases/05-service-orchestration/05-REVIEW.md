---
phase: 05-service-orchestration
reviewed: 2026-05-24T00:00:00Z
depth: quick
files_reviewed: 3
files_reviewed_list:
  - src/carpix_images/services/image_service.py
  - src/carpix_images/services/__init__.py
  - tests/unit/test_image_service.py
findings:
  critical: 2
  warning: 2
  info: 0
  total: 4
status: issues_found
---

# Phase 05: Code Review Report

**Reviewed:** 2026-05-24
**Depth:** quick (with targeted logic tracing on flagged patterns)
**Files Reviewed:** 3
**Status:** issues_found

## Summary

Reviewed the ImageService orchestration layer and its unit test suite. Two blockers were found: the self-healing mechanism is dead code (the `try/except FileNotFoundError` around `FileResponse` construction can never trigger, because `FileResponse` is lazy and never raises at construction time), and network errors during image download propagate as unhandled 500s in violation of the project's "never a 500" constraint. Two warnings were found: the `file_title` field is systematically wrong for Wikimedia thumbnail URLs, and the self-healing test suite provides false confidence because it mocks the behavior that cannot occur in production.

---

## Critical Issues

### CR-01: Self-healing is dead code — FileResponse never raises FileNotFoundError at construction

**File:** `src/carpix_images/services/image_service.py:44-48`

**Issue:** The self-healing block wraps `self._storage.file_response(...)` in a `try/except FileNotFoundError`. However, `StorageService.file_response()` constructs a `fastapi.responses.FileResponse` object, which is lazy — it does not open or stat the file at construction time. `FileNotFoundError` is never raised here. The except branch is unreachable dead code.

When the DB has a valid cache entry but the file is absent from disk (e.g., volume was wiped), the service returns a `FileResponse` pointing to a nonexistent path. When FastAPI's ASGI layer later attempts to send the response body, it encounters the missing file and returns a 500, violating the project's "never a 500" constraint.

Verified: `FileResponse(path='/nonexistent/path/image.jpg', media_type='image/jpeg')` raises no exception.

**Fix:** Check for file existence explicitly before constructing the `FileResponse`, using `anyio.Path.exists()` to stay async-safe:

```python
# Step b: cache hit — attempt to serve from local file
if entry is not None:
    file_path = self._storage.path_for(brand_key, model_key, year)
    if await anyio.Path(file_path).exists():
        return self._storage.file_response(brand_key, model_key, year)
    # else fall through to self-healing re-fetch
```

`StorageService` needs a companion `path_for()` method (synchronous, returning the resolved `Path`) so the service can check existence without duplicating path logic. Alternatively, add an async `exists()` method to `StorageService` directly.

---

### CR-02: httpx network errors during image download propagate as unhandled 500s

**File:** `src/carpix_images/services/image_service.py:59-62`

**Issue:** The image download block creates a bare `httpx.AsyncClient`, calls `client.get(url)`, and calls `response.raise_for_status()`. Neither `httpx.RequestError` (network failure, timeout, DNS error) nor `httpx.HTTPStatusError` (4xx/5xx from the CDN) is caught. Both propagate as unhandled exceptions, which FastAPI converts to HTTP 500 responses.

The project constraint is explicit: "Extraction failures always 404, never 500." A CDN returning 403/404 or a transient network error during download is an extraction failure and must produce a 404.

```python
async with httpx.AsyncClient() as client:
    response = await client.get(url, timeout=httpx.Timeout(30.0))
    response.raise_for_status()   # <-- raises HTTPStatusError, no catch
    image_bytes: bytes = response.content
```

**Fix:** Wrap the download block in a try/except and convert failures to 404:

```python
try:
    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=httpx.Timeout(30.0))
        response.raise_for_status()
        image_bytes: bytes = response.content
except (httpx.HTTPStatusError, httpx.RequestError) as exc:
    raise HTTPException(
        status_code=404,
        detail="Image could not be retrieved from source",
    ) from exc
```

---

## Warnings

### WR-01: file_title is systematically wrong for Wikimedia thumbnail URLs

**File:** `src/carpix_images/services/image_service.py:70`

**Issue:** The `file_title` is extracted as `url.rsplit("/", 1)[-1]`. Wikimedia CDN thumbnail URLs follow the pattern:

```
https://upload.wikimedia.org/wikipedia/commons/thumb/a/b/Toyota_Corolla.jpg/800px-Toyota_Corolla.jpg
```

`rsplit("/", 1)[-1]` yields `800px-Toyota_Corolla.jpg` — a CDN derivative filename, not the Commons page title. The actual file title is `Toyota_Corolla.jpg`. If `file_title` is ever used to construct a Commons page URL, attribution link, or API query, the `800px-` prefix will cause those lookups to fail silently or return wrong results.

**Fix:** Strip the `800px-` (or more generally, any `{width}px-`) prefix when extracting the title:

```python
import re

raw_title = url.rsplit("/", 1)[-1]
# Remove Wikimedia thumbnail prefix like "800px-" or "1200px-"
file_title = re.sub(r"^\d+px-", "", raw_title)
```

---

### WR-02: CACHE-04a self-healing test provides false confidence

**File:** `tests/unit/test_image_service.py:125-143`

**Issue:** The test `test_self_healing_when_db_hit_but_file_absent` sets `storage_file_response_side_effect=[FileNotFoundError("missing"), good_response]` — that is, the mock is configured to raise `FileNotFoundError` on the first call. This exercises the catch branch in `image_service.py:46-48`.

However, as documented in CR-01, the real `StorageService.file_response()` can never raise `FileNotFoundError`. The test passes against a mock that simulates impossible production behavior. When the real service is used, the self-healing path does not execute, but the test reports it as working. This provides false confidence and masks the CR-01 defect.

The test must be rewritten once CR-01 is fixed to use the file-existence-check mechanism instead.

**Fix:** After fixing CR-01 (using an async `exists()` check), rewrite the test to mock `anyio.Path.exists()` (or `StorageService.exists()`) returning `False` on the first call, then `True` on subsequent calls. Verify Wikimedia is called once and a `FileResponse` is returned.

---

_Reviewed: 2026-05-24_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: quick (with targeted logic tracing)_
