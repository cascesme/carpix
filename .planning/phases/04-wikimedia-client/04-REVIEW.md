---
phase: 04-wikimedia-client
reviewed: 2026-05-24T00:00:00Z
depth: quick
files_reviewed: 2
files_reviewed_list:
  - src/carpix_images/services/wikimedia.py
  - tests/unit/test_wikimedia.py
findings:
  critical: 2
  warning: 2
  info: 1
  total: 5
status: issues_found
---

# Phase 04: Code Review Report

**Reviewed:** 2026-05-24
**Depth:** quick
**Files Reviewed:** 2
**Status:** issues_found

## Summary

Reviewed `WikimediaClient` implementation and its unit test suite. The core logic
for querying Wikimedia Commons and filtering JPEG results is structurally sound.
However, two critical defects were found: (1) the `_USER_AGENT` constant is defined
but never sent, violating Wikimedia's mandatory User-Agent policy and risking request
rejection; (2) `info["thumburl"]` is accessed with a bare key lookup that will raise
`KeyError` if the Wikimedia API returns a JPEG entry without a `thumburl` (which can
happen when the CDN thumb is unavailable). Two warnings cover unhandled HTTP/network
exceptions that propagate to callers and an unclosed `AsyncClient` in the test fixture.

---

## Critical Issues

### CR-01: `_USER_AGENT` defined but never sent — Wikimedia requests sent without required header

**File:** `src/carpix_images/services/wikimedia.py:8,35`

**Issue:** `_USER_AGENT` is assigned at module level but is never passed as a header to
the `httpx.AsyncClient` GET call. Wikimedia Commons explicitly requires a descriptive
`User-Agent` header on all API requests and will throttle or block requests that carry
only `python-httpx/<version>`. This is a correctness and reliability failure: all
production requests will be made with the wrong identity, risking HTTP 429 / 403
responses from the Wikimedia API.

**Fix:** Pass the header either at client construction time (preferred, so every call
carries it) or per request:

```python
# Option A — inject at client construction (in DI wiring or fixture):
httpx.AsyncClient(headers={"User-Agent": _USER_AGENT})

# Option B — pass per-call inside _search_first_jpeg:
response = await self._client.get(
    _COMMONS_API,
    params=params,
    headers={"User-Agent": _USER_AGENT},
)
```

Option A is preferable so the constant is used at every call automatically.

---

### CR-02: Bare `info["thumburl"]` raises `KeyError` when key is absent

**File:** `src/carpix_images/services/wikimedia.py:49`

**Issue:** The Wikimedia API omits `thumburl` from `imageinfo` when the thumb cannot be
generated (e.g., very large source file, CDN error, or when `iiurlwidth` is not
honoured). The code does:

```python
return str(info["thumburl"])
```

If `thumburl` is missing, this raises an uncaught `KeyError`, which propagates out of
`find_jpeg_url` and will surface as an unhandled exception (HTTP 500) in the FastAPI
handler — directly violating the project's core constraint: "Extraction failures always
404, never 500."

**Fix:** Use `.get()` and skip entries without a thumb:

```python
thumb = info.get("thumburl")
if thumb and info.get("mime") == "image/jpeg":
    return str(thumb)
```

---

## Warnings

### WR-01: `raise_for_status()` exception is not caught — HTTP errors propagate as 500

**File:** `src/carpix_images/services/wikimedia.py:36`

**Issue:** `response.raise_for_status()` raises `httpx.HTTPStatusError` on 4xx/5xx
responses from Wikimedia. `_search_first_jpeg` has no `try/except` around the HTTP
call, so transient Wikimedia errors (rate-limits, server errors) will bubble up through
`find_jpeg_url` to the FastAPI route handler as an unhandled exception — a 500, not a
404. Network errors (`httpx.RequestError`, timeouts) have the same problem.

The project constraint is "never a 500, always a FileResponse or a clean 404."

**Fix:** Wrap the network call and treat failures as "no result":

```python
try:
    response = await self._client.get(_COMMONS_API, params=params)
    response.raise_for_status()
except (httpx.HTTPStatusError, httpx.RequestError):
    return None
```

---

### WR-02: Test fixture creates an `AsyncClient` that is never closed — resource leak

**File:** `tests/unit/test_wikimedia.py:14-16`

**Issue:** The `wiki_client` fixture instantiates `httpx.AsyncClient()` directly without
using it as an async context manager and without calling `.aclose()`. The client holds
open connection pool resources for the lifetime of the test session. While this will not
cause test failures today (respx intercepts all requests at transport level), it
generates `ResourceWarning` from asyncio and is a bad pattern that masks real leaks if
the test suite grows.

```python
@pytest.fixture()
def wiki_client() -> WikimediaClient:
    return WikimediaClient(httpx.AsyncClient())   # never closed
```

**Fix:** Convert to an async fixture with proper teardown:

```python
@pytest.fixture()
async def wiki_client() -> AsyncGenerator[WikimediaClient, None]:
    async with httpx.AsyncClient() as client:
        yield WikimediaClient(client)
```

---

## Info

### IN-01: `_USER_AGENT` contains a placeholder GitHub URL — hardcoded stub

**File:** `src/carpix_images/services/wikimedia.py:8`

**Issue:** The user-agent string references `https://github.com/user/carpix`, which is a
placeholder. Wikimedia's policy requires the URL to identify the actual project or
contact so they can reach out if the client misbehaves.

```python
_USER_AGENT = "carpix-images/0.1 (https://github.com/user/carpix)"
```

**Fix:** Replace with the real repository URL or a contact email before deploying:

```python
_USER_AGENT = "carpix-images/0.1 (https://github.com/cesarcastro/carpix; cesarcastro15@gmail.com)"
```

---

_Reviewed: 2026-05-24_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: quick_
