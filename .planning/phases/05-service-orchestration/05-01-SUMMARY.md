---
phase: 05-service-orchestration
plan: "01"
subsystem: services
tags: [tdd, image-service, red-baseline, cache]
dependency_graph:
  requires:
    - 04-02-SUMMARY.md  # WikimediaClient implemented
    - 03-02-SUMMARY.md  # CacheRepository implemented
    - 02-01-SUMMARY.md  # StorageService implemented
  provides:
    - ImageService stub (get_or_fetch raises NotImplementedError)
    - 5 failing RED tests specifying ImageService contract
  affects:
    - src/carpix_images/services/image_service.py
    - src/carpix_images/services/__init__.py
    - tests/unit/test_image_service.py
tech_stack:
  added: []
  patterns:
    - TDD RED baseline: stub raises NotImplementedError, tests drive implementation
    - Dependency injection: StorageService, CacheRepository, WikimediaClient injected at construction
    - Per-key asyncio.Lock dict declared in __init__ for mypy compliance
key_files:
  created:
    - src/carpix_images/services/image_service.py
    - tests/unit/test_image_service.py
  modified:
    - src/carpix_images/services/__init__.py
decisions:
  - ImageService constructor injects all three dependencies (storage, repo, wikimedia) for SOLID/testability
  - self._locks declared as empty dict[tuple[str, str, int], asyncio.Lock] in __init__ for mypy compliance; locking logic deferred to Plan 02 implementation
  - Tests use unittest.mock.AsyncMock/MagicMock — no real DB or HTTP in unit layer
  - respx_mock used only for tests that exercise httpx download call (cache-miss, concurrent, self-healing); Wikimedia client itself mocked via AsyncMock
metrics:
  duration: "~2 minutes"
  completed: "2026-05-24"
  tasks_completed: 1
  files_created: 3
---

# Phase 05 Plan 01: ImageService RED Baseline Summary

**One-liner:** ImageService stub + 5 failing TDD RED tests specifying cache-hit, cache-miss, concurrent serialization, self-healing, and 404 behaviors.

## What Was Built

- `src/carpix_images/services/image_service.py` — `ImageService` class stub with:
  - Constructor accepting `storage: StorageService`, `repo: CacheRepository`, `wikimedia: WikimediaClient`
  - `async def get_or_fetch(brand, model, year) -> FileResponse` raising `NotImplementedError`
  - `self._locks: dict[tuple[str, str, int], asyncio.Lock] = {}` declared for per-key locking (implemented in Plan 02)
- `src/carpix_images/services/__init__.py` — exports `ImageService` from `carpix_images.services`
- `tests/unit/test_image_service.py` — 5 async unit tests (module-level, flat style matching test_wikimedia.py):
  1. `test_cache_hit_returns_file_response_without_wikimedia_call` — cache hit, no Wikimedia call
  2. `test_cache_miss_fetches_saves_inserts_and_returns_file_response` — full fetch pipeline
  3. `test_concurrent_requests_for_same_key_trigger_exactly_one_wikimedia_fetch` — per-key lock
  4. `test_self_healing_when_db_hit_but_file_absent` — DB hit + file missing → re-fetch
  5. `test_raises_http_exception_404_when_no_image_found` — Wikimedia returns None → 404

## RED Gate Verification

```
FAILED tests/unit/test_image_service.py::test_cache_hit_returns_file_response_without_wikimedia_call
FAILED tests/unit/test_image_service.py::test_cache_miss_fetches_saves_inserts_and_returns_file_response
FAILED tests/unit/test_image_service.py::test_concurrent_requests_for_same_key_trigger_exactly_one_wikimedia_fetch
FAILED tests/unit/test_image_service.py::test_self_healing_when_db_hit_but_file_absent
FAILED tests/unit/test_image_service.py::test_raises_http_exception_404_when_no_image_found
5 failed in 0.45s
```

All 5 tests fail with `NotImplementedError` — RED gate confirmed.

## TDD Gate Compliance

- RED gate commit: `05c3b07` — `test(05-01): add 5 failing RED tests for ImageService`
- GREEN gate: deferred to Plan 02 (`feat(05-02): implement ImageService`)

## Deviations from Plan

None — plan executed exactly as written.

Two minor ruff E501 (line-too-long) violations were auto-fixed before commit (Rule 1 — code quality), both in the test helper function.

## Commits

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Scaffold ImageService stub and RED test baseline | 05c3b07 | image_service.py, __init__.py, test_image_service.py |

## Self-Check: PASSED

| Item | Status |
|------|--------|
| src/carpix_images/services/image_service.py | FOUND |
| src/carpix_images/services/__init__.py | FOUND |
| tests/unit/test_image_service.py | FOUND |
| .planning/phases/05-service-orchestration/05-01-SUMMARY.md | FOUND |
| commit 05c3b07 | FOUND |
