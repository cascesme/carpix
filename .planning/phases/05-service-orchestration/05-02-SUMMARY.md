---
phase: 05-service-orchestration
plan: "02"
subsystem: services
tags: [tdd, green, image-service, cache-aside, asyncio-lock, self-healing]
dependency_graph:
  requires:
    - 05-01-SUMMARY.md  # ImageService stub + 5 RED tests
    - 04-02-SUMMARY.md  # WikimediaClient implemented
    - 03-02-SUMMARY.md  # CacheRepository implemented
    - 02-01-SUMMARY.md  # StorageService implemented
  provides:
    - ImageService full implementation (get_or_fetch)
    - All 5 CACHE-0x tests GREEN
    - Full test suite 32/32 passing
  affects:
    - src/carpix_images/services/image_service.py
tech_stack:
  added: []
  patterns:
    - Cache-aside pattern: DB find → file_response or Wikimedia fetch → save → insert → file_response
    - Per-key asyncio.Lock dict serializes concurrent requests for identical (brand_key, model_key, year)
    - Self-healing: FileNotFoundError on file_response triggers transparent re-fetch instead of 500
    - canonical_key normalization applied before all DB/storage operations; original strings to Wikimedia
    - httpx.AsyncClient created internally as async context manager with 30s timeout
key_files:
  created: []
  modified:
    - src/carpix_images/services/image_service.py
decisions:
  - "Catch FileNotFoundError from file_response rather than Path.exists() check — matches test contract and avoids TOCTOU race"
  - "Pass original (un-normalized) brand/model to WikimediaClient.find_jpeg_url per plan spec (better search quality)"
  - "Lock key is tuple(brand_key, model_key, year) so normalized variants map to same lock slot"
  - "httpx.AsyncClient created internally (not injected) — respx_mock intercepts at transport layer without injection"
metrics:
  duration: "~5 minutes"
  completed: "2026-05-24"
  tasks_completed: 2
  files_created: 1
  files_modified: 1
---

# Phase 05 Plan 02: ImageService GREEN Implementation Summary

**One-liner:** ImageService.get_or_fetch() fully implemented — cache-aside with per-key asyncio.Lock, self-healing re-fetch, and HTTPException 404 on Wikimedia miss; all 5 RED tests turned GREEN, 32/32 suite passing.

## What Was Built

- `src/carpix_images/services/image_service.py` — Full `ImageService.get_or_fetch()` implementation:
  - Normalizes brand/model via `canonical_key()` for all DB/storage operations
  - Per-key `asyncio.Lock` serialization: dict keyed on `(brand_key, model_key, year)` prevents double-fetch races
  - Cache hit: calls `self._storage.file_response()` directly; catches `FileNotFoundError` for self-healing
  - Self-healing path: DB hit with missing local file falls through to Wikimedia re-fetch transparently
  - Cache miss: `WikimediaClient.find_jpeg_url()` → `httpx.AsyncClient` GET (30s timeout) → `StorageService.save()` → `CacheRepository.insert()` → `file_response()`
  - Raises `HTTPException(status_code=404)` when Wikimedia returns `None`

## GREEN Gate Verification

```
tests/unit/test_image_service.py::test_cache_hit_returns_file_response_without_wikimedia_call PASSED
tests/unit/test_image_service.py::test_cache_miss_fetches_saves_inserts_and_returns_file_response PASSED
tests/unit/test_image_service.py::test_concurrent_requests_for_same_key_trigger_exactly_one_wikimedia_fetch PASSED
tests/unit/test_image_service.py::test_self_healing_when_db_hit_but_file_absent PASSED
tests/unit/test_image_service.py::test_raises_http_exception_404_when_no_image_found PASSED
5 passed in 0.40s
```

## Full Suite

```
32 passed in 2.47s
```

All 32 tests pass (5 integration + 27 unit). Zero failures.

## TDD Gate Compliance

- RED gate commit: `05c3b07` — `test(05-01): add 5 failing RED tests for ImageService` (Plan 01)
- GREEN gate commit: `00cf8eb` — `feat(05-02): implement ImageService GREEN — all 5 tests passing`
- REFACTOR gate: not needed — implementation was clean on first pass

## Linting / Type Checks

- `uv run ruff check src/ tests/` — exit 0, all checks passed
- `uv run mypy --strict src/` — exit 0, success: no issues found in 13 source files

## Phase 5 Success Criteria Map

| Criterion | Test | Status |
|-----------|------|--------|
| SC1 (CACHE-01) | test_cache_hit_returns_file_response_without_wikimedia_call | PASSED |
| SC2 (CACHE-02) | test_cache_miss_fetches_saves_inserts_and_returns_file_response | PASSED |
| SC3 (CACHE-03) | test_concurrent_requests_for_same_key_trigger_exactly_one_wikimedia_fetch | PASSED |
| SC4 (CACHE-04) | test_self_healing_when_db_hit_but_file_absent | PASSED |
| SC5 (CACHE-04b) | test_raises_http_exception_404_when_no_image_found | PASSED |

## Deviations from Plan

None — plan executed exactly as written.

Task 2 (ruff + mypy clean) required zero code changes; the implementation passed both tools on first run.

## Known Stubs

None — get_or_fetch is fully implemented. All data flows are wired to real dependencies.

## Threat Flags

No new network endpoints, auth paths, file access patterns, or schema changes introduced.
Existing threat mitigations verified:
- T-05-02-I (path traversal): StorageService._validated_path enforces is_relative_to() — unchanged
- T-05-02-D (lock hold): async with context manager guarantees lock release on all paths including exception
- T-05-02-E (SSRF): thumburl sourced only from WikimediaClient; canonical_key strips traversal chars

## Commits

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Implement ImageService GREEN | 00cf8eb | image_service.py |
| 2 | ruff + mypy --strict clean (no changes needed) | — | — |

## Self-Check: PASSED

| Item | Status |
|------|--------|
| src/carpix_images/services/image_service.py | FOUND |
| .planning/phases/05-service-orchestration/05-02-SUMMARY.md | FOUND |
| commit 00cf8eb | FOUND |
| 5 image_service tests passing | VERIFIED |
| 32 total tests passing | VERIFIED |
| ruff check exit 0 | VERIFIED |
| mypy --strict exit 0 | VERIFIED |
