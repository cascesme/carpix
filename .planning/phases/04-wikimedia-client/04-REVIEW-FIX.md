---
phase: 04-wikimedia-client
fixed_at: 2026-05-24T00:00:00Z
review_path: .planning/phases/04-wikimedia-client/04-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 04: Code Review Fix Report

**Fixed at:** 2026-05-24
**Source review:** `.planning/phases/04-wikimedia-client/04-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 4 (Critical + Warning)
- Fixed: 4
- Skipped: 0

## Fixed Issues

### CR-01: `_USER_AGENT` never sent

**Files modified:** `src/carpix_images/services/wikimedia.py`
**Commit:** 6b0dfcb
**Applied fix:** Added `headers={"User-Agent": _USER_AGENT}` as a keyword argument to `self._client.get(...)` inside `_search_first_jpeg` (Option B — per-call, safer than mutating the injected client).

---

### CR-02: Bare `info["thumburl"]` raises `KeyError`

**Files modified:** `src/carpix_images/services/wikimedia.py`
**Commit:** 530b068
**Applied fix:** Replaced `return str(info["thumburl"])` with a two-step safe access: `thumb = info.get("thumburl")` followed by `if thumb and info.get("mime") == "image/jpeg": return str(thumb)`. Entries without `thumburl` are now silently skipped rather than raising `KeyError`.

---

### WR-01: `raise_for_status()` uncaught

**Files modified:** `src/carpix_images/services/wikimedia.py`
**Commit:** d170123
**Applied fix:** Wrapped the `self._client.get(...)` call and `response.raise_for_status()` in a `try/except (httpx.HTTPStatusError, httpx.RequestError): return None` block. Both HTTP error responses (4xx/5xx) and network failures (timeouts, connection errors) now return `None` instead of propagating to the FastAPI handler as a 500.

---

### WR-02: Test fixture `AsyncClient` never closed

**Files modified:** `tests/unit/test_wikimedia.py`
**Commit:** 0ac8d67
**Applied fix:** Converted the synchronous `wiki_client` fixture to an async generator fixture using `async with httpx.AsyncClient() as client: yield WikimediaClient(client)`. Added `from collections.abc import AsyncGenerator` import. The client is now properly closed after each test.

---

## Skipped Issues

None — all findings were fixed.

---

_Fixed: 2026-05-24_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
