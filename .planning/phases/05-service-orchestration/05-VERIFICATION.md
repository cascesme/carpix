---
phase: 05-service-orchestration
verified: 2026-05-24T12:00:00Z
status: passed
score: 11/11 must-haves verified
overrides_applied: 0
re_verification: false
---

# Phase 05: Service Orchestration Verification Report

**Phase Goal:** Implement ImageService — the orchestration layer that ties WikimediaClient, ImageStorage, and ImageRepository into a single cache-aside flow.

**Verified:** 2026-05-24T12:00:00Z
**Status:** PASSED
**Score:** 11/11 observable truths verified

## Goal Achievement

### Observable Truths (Phase 05-01 + 05-02 Combined)

| # | Truth | Status | Evidence |
| --- | ------- | ---------- | -------------- |
| 1 | 5 unit tests for ImageService exist and specify all cache behaviors (RED baseline) | ✓ VERIFIED | tests/unit/test_image_service.py contains 5 async test functions |
| 2 | ImageService class with dependency injection for storage, repo, wikimedia | ✓ VERIFIED | src/carpix_images/services/image_service.py lines 17-26 |
| 3 | ImageService importable from carpix_images.services | ✓ VERIFIED | from carpix_images.services import ImageService works without error |
| 4 | Cache-hit returns FileResponse without contacting Wikimedia | ✓ VERIFIED | test_cache_hit passes; wikimedia.find_jpeg_url.assert_not_called() confirmed |
| 5 | Cache-miss triggers full fetch → save → insert → FileResponse pipeline | ✓ VERIFIED | test_cache_miss passes; storage.save and repo.insert called once each |
| 6 | Concurrent requests serialized per-key via asyncio.Lock to prevent double-fetch | ✓ VERIFIED | test_concurrent passes; find_jpeg_url.call_count == 1 despite asyncio.gather(2) |
| 7 | DB hit with missing file triggers self-healing re-fetch (no 500 error) | ✓ VERIFIED | test_self_healing passes; FileNotFoundError caught, re-fetch initiated |
| 8 | Wikimedia returns None → HTTPException 404 raised | ✓ VERIFIED | test_404 passes; exc_info.value.status_code == 404 confirmed |
| 9 | Per-key asyncio.Lock dict declared and used for serialization | ✓ VERIFIED | self._locks: dict[tuple[str, str, int], asyncio.Lock] declared, lock acquired on lines 34-38 |
| 10 | canonical_key normalization applied to brand and model before all DB/storage operations | ✓ VERIFIED | Lines 31-32 call canonical_key() before using normalized keys in all lookups |
| 11 | ruff and mypy --strict both pass on full codebase | ✓ VERIFIED | ruff check exit 0; mypy --strict exit 0 (13 source files checked) |

**Score:** 11/11 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | ----------- | ------ | ------- |
| `src/carpix_images/services/image_service.py` | ImageService class with full get_or_fetch implementation | ✓ VERIFIED | File exists, 84 lines, full cache-aside implementation with all 8 steps (a-h) |
| `tests/unit/test_image_service.py` | 5 async unit tests covering cache-hit, miss, concurrent, self-healing, 404 | ✓ VERIFIED | File exists, 5 test functions, all PASSED (previously RED baseline) |
| `src/carpix_images/services/__init__.py` | Export ImageService | ✓ VERIFIED | File exports ImageService from .image_service |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | --- | --- | ------ | ------- |
| image_service.py | cache_repository.py | await self._repo.find() / insert() | ✓ WIRED | Lines 40, 73-80; both repo methods called within lock |
| image_service.py | wikimedia.py | await self._wikimedia.find_jpeg_url() | ✓ WIRED | Line 51; called in cache-miss path, returns URL or None |
| image_service.py | storage.py | await self._storage.save() / file_response() | ✓ WIRED | Lines 45, 65-67, 83; save on cache-miss, file_response on all success paths |
| test_image_service.py | image_service.py | from ... import ImageService | ✓ WIRED | Line 16; import exists, all 5 tests use it |

### Data-Flow Trace (Artifacts that Render/Return Dynamic Data)

ImageService is a cache orchestration service that processes and returns FileResponse objects. The data flow verification:

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| image_service.py get_or_fetch() | entry (DB lookup) | self._repo.find() | Query returns CacheEntry or None | ✓ FLOWING |
| image_service.py get_or_fetch() | url (Wikimedia) | self._wikimedia.find_jpeg_url() | Query returns thumburl string or None | ✓ FLOWING |
| image_service.py get_or_fetch() | image_bytes | httpx.AsyncClient().get(url) | HTTP response.content returns actual bytes | ✓ FLOWING |
| image_service.py get_or_fetch() | saved_path | self._storage.save(...) | Returns Path object pointing to written file | ✓ FLOWING |
| image_service.py get_or_fetch() | return value | self._storage.file_response() | Returns FileResponse wrapping local path | ✓ FLOWING |

All data flows are real (not hardcoded empty, not mocked static values in production code). Tests use mock objects, but production code receives real data from dependencies.

### Requirements Coverage

| Requirement | Test | Description | Status | Evidence |
| ----------- | ---- | ----------- | ------ | -------- |
| CACHE-01 | test_cache_hit_returns_file_response_without_wikimedia_call | Cache-hit path: DB hit returns FileResponse from local file; Wikimedia is never contacted | ✓ VERIFIED | Line 78: assert_not_called() confirms no Wikimedia call; cache hit → file_response directly |
| CACHE-02 | test_cache_miss_fetches_saves_inserts_and_returns_file_response | Cache-miss path: DB miss triggers full Wikimedia fetch, saves file, inserts DB row, returns FileResponse | ✓ VERIFIED | Lines 98-99: storage.save and repo.insert both called once; full pipeline executed |
| CACHE-03 | test_concurrent_requests_for_same_key_trigger_exactly_one_wikimedia_fetch | Concurrent requests for same uncached vehicle serialized via per-key asyncio.Lock — prevents duplicate fetches | ✓ VERIFIED | Line 122: call_count == 1 despite two concurrent asyncio.gather calls; lock prevents race |
| CACHE-04 | test_self_healing_when_db_hit_but_file_absent | DB hit but local file missing triggers re-fetch instead of 500 | ✓ VERIFIED | Line 143: find_jpeg_url called once; FileNotFoundError caught on line 46, re-fetch initiated |

**All phase-required requirements satisfied:** 4/4 CACHE requirements implemented and tested.

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
| ---- | ------- | -------- | ------ |
| (none) | No debt markers (TBD, FIXME, XXX, TODO) | — | ✓ Clean |
| (none) | No stubs (return None, return {}, raise NotImplementedError) | — | ✓ Full implementation |
| (none) | No console-only handlers | — | ✓ Real data flows |

### Test Suite Results

| Category | Result |
| -------- | ------ |
| ImageService tests (5) | 5 PASSED |
| Full suite (32) | 32 PASSED, 0 FAILED |
| Regression check | 27 prior tests still PASSING |
| Execution time | 2.42 seconds |

### Linting and Type Checking

| Tool | Status | Details |
| ---- | ------ | ------- |
| ruff check src/ tests/ | ✓ EXIT 0 | All checks passed; no violations |
| mypy --strict src/ | ✓ EXIT 0 | Success: no issues found in 13 source files |

## Implementation Details

### Cache-Aside Pattern (Lines 39-83)

The implementation follows a strict cache-aside pattern inside a per-key asyncio.Lock:

1. **DB Lookup** (line 40): `entry = await self._repo.find(brand_key, model_key, year)`
2. **Cache Hit** (lines 43-48): If entry found, attempt to return file. If FileNotFoundError occurs (self-healing), fall through.
3. **Wikimedia Fetch** (line 51): `url = await self._wikimedia.find_jpeg_url(brand, model, year)` — note original (non-normalized) brand/model passed
4. **404 on Miss** (lines 52-56): If url is None, raise HTTPException 404
5. **HTTP Download** (lines 59-62): Create httpx.AsyncClient, GET with 30s timeout, extract bytes
6. **File Save** (lines 65-67): `await self._storage.save(brand_key, model_key, year, image_bytes)`
7. **DB Insert** (lines 73-80): `await self._repo.insert(...)` with file_title extracted from URL
8. **Return** (line 83): `return self._storage.file_response(brand_key, model_key, year)`

### Per-Key Locking (Lines 34-38)

Concurrent requests for the same vehicle (same brand_key, model_key, year tuple) acquire a shared asyncio.Lock:

```python
lock_key = (brand_key, model_key, year)
if lock_key not in self._locks:
    self._locks[lock_key] = asyncio.Lock()

async with self._locks[lock_key]:
    # cache-aside logic
```

This ensures that two concurrent callers for the same vehicle:
1. First caller acquires lock, finds miss, fetches from Wikimedia, saves, inserts
2. Second caller acquires lock after first completes, finds cache hit, returns immediately
Result: **exactly one Wikimedia fetch**, not two — confirmed by test line 122.

### Self-Healing (Lines 44-48)

When the DB reports a cache hit but the local file is missing (e.g., file deleted after cache entry created):

```python
try:
    return self._storage.file_response(brand_key, model_key, year)
except FileNotFoundError:
    # Self-healing: file missing on disk, fall through to re-fetch
    pass
```

Rather than returning a 500 error, the code falls through to the Wikimedia re-fetch logic. This is tested in test_self_healing (line 125-143) where storage.file_response raises FileNotFoundError on first call (cache hit, but file missing) and then returns normally on second call (after re-fetch).

### Normalization (Lines 31-32)

Brand and model are normalized before all DB and storage operations:

```python
brand_key = canonical_key(brand)
model_key = canonical_key(model)
```

The original (non-normalized) brand and model are passed to WikimediaClient.find_jpeg_url() per plan specification, because Wikimedia search benefits from the original casing (e.g., "Toyota Corolla" vs "toyotacorolla").

### Error Handling (Lines 52-56)

When Wikimedia returns None (no image found):

```python
if url is None:
    raise HTTPException(
        status_code=404,
        detail="No image found for this vehicle",
    )
```

This ensures clean 404 responses, never 500 errors. Tested in test_raises_http_exception_404_when_no_image_found.

## Commits

| Plan | Task | Commit | Files | Status |
|------|------|--------|-------|--------|
| 05-01 | Scaffold ImageService stub and RED test baseline | 05c3b07 | image_service.py, __init__.py, test_image_service.py | ✓ VERIFIED |
| 05-02 | Implement ImageService GREEN — all 5 tests passing | 00cf8eb | image_service.py | ✓ VERIFIED |

Both commits verified to exist in git history with correct messages and affected files.

## Summary

**Phase 05 achieves its goal completely.** The ImageService orchestrates the cache-aside pattern, tying together WikimediaClient (Wikimedia Commons search and CDN download), CacheRepository (DB lookups and inserts), and StorageService (local filesystem persistence) into a single coherent service with:

- ✓ Cache-hit optimization (no external calls)
- ✓ Cache-miss full pipeline (fetch → save → insert → serve)
- ✓ Concurrent request serialization (per-key lock prevents races)
- ✓ Self-healing on missing files (transparent re-fetch, no 500 errors)
- ✓ Clean 404 on no-image scenarios

All 4 phase-required CACHE requirements (CACHE-01 through CACHE-04) are satisfied, tested, and verified to work correctly. Zero regressions, zero linting violations, zero type errors, zero debt markers.

---

_Verified: 2026-05-24T12:00:00Z_
_Verifier: Claude (gsd-verifier)_
