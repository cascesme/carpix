---
phase: 06-router-e2e-integration
plan: "01"
subsystem: router-tdd-red
tags: [tdd, red-baseline, router, integration-tests, unit-tests]
dependency_graph:
  requires: [05-01, 05-02]
  provides: [06-02]
  affects: [src/carpix_images/routers/images.py, src/carpix_images/services/image_service.py, tests/unit/test_image_service.py, tests/integration/test_images_router.py, src/carpix_images/main.py]
tech_stack:
  added: []
  patterns: [TDD-RED, ASGITransport, respx-mock, tuple-return-type]
key_files:
  created:
    - src/carpix_images/routers/images.py
    - tests/integration/test_images_router.py
  modified:
    - src/carpix_images/services/image_service.py
    - tests/unit/test_image_service.py
    - src/carpix_images/main.py
decisions:
  - "Router stub included in main.py at RED stage so NotImplementedError is visible as 500 in integration tests"
  - "ImageService.get_or_fetch() return type changed to tuple[FileResponse, bool] with stub body"
metrics:
  duration: "4 minutes"
  completed: "2026-05-24T13:23:46Z"
  tasks_completed: 3
  files_changed: 5
---

# Phase 06 Plan 01: TDD RED Baseline — Router Stub + Integration Tests Summary

**One-liner:** Images router stub + ImageService tuple return type + 5 rewritten unit tests + 5 new integration tests, all failing RED.

## What Was Built

Established the TDD RED baseline for Phase 6:

1. **`src/carpix_images/routers/images.py`** — New stub router exporting `router = APIRouter()` with a single `GET /v1/images/{brand}/{model}/{year}` route whose body is `raise NotImplementedError`.

2. **`src/carpix_images/services/image_service.py`** — `get_or_fetch()` return type changed from `-> FileResponse` to `-> tuple[FileResponse, bool]`; full implementation replaced with `raise NotImplementedError`. All 52 lines of previous implementation removed.

3. **`tests/unit/test_image_service.py`** — 4 of 5 tests rewritten to unpack `response, cache_hit = await svc.get_or_fetch(...)` and assert correct boolean values (True for cache hit, False for miss/self-healing). Concurrent test uses `(r0, hit0), (r1, hit1) = responses`.

4. **`tests/integration/test_images_router.py`** — 5 new integration tests using `ASGITransport(app=create_app())`, `respx_mock`, and `testcontainers` (via `postgres_container` fixture). Tests cover cache miss X-Cache header, cache hit X-Cache header, 404 no result, brand/model normalization, and content-type.

5. **`src/carpix_images/main.py`** — Images router registered via `application.include_router(images_router)`.

## Verification Results

| Check | Result |
|-------|--------|
| `pytest --collect-only tests/integration/test_images_router.py` | 5 tests, 0 errors |
| `pytest tests/unit/test_image_service.py` | 5 FAILED (RED — NotImplementedError) |
| `pytest tests/integration/test_images_router.py` | 5 FAILED (RED — NotImplementedError 500) |
| `pytest tests/unit/ tests/integration/test_cache_repository.py` | 27 passed GREEN |

## Task Commits

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Stub images router + update ImageService return type | fcdacda | src/carpix_images/routers/images.py, src/carpix_images/services/image_service.py |
| 2 | Rewrite unit tests to unpack (response, cache_hit) tuple | 840588f | tests/unit/test_image_service.py |
| 3 | Write 5 integration tests for images router | 5280e11 | tests/integration/test_images_router.py, src/carpix_images/main.py |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Included images_router in main.py during Task 3**
- **Found during:** Task 3 verification
- **Issue:** Without including the router in main.py, integration tests received 404 (route not found) instead of 500 (NotImplementedError from stub). The plan specified "NotImplementedError from stub router" causing 500 responses as the expected RED failure mode.
- **Fix:** Added `from carpix_images.routers.images import router as images_router` and `application.include_router(images_router)` to main.py during Task 3 commit.
- **Files modified:** src/carpix_images/main.py
- **Commit:** 5280e11

## TDD Gate Compliance

- RED gate: Task 1 commit `fcdacda` — stub with NotImplementedError
- Tests rewritten: Task 2 commit `840588f`
- Integration tests written: Task 3 commit `5280e11`
- GREEN gate: deferred to 06-02

## Known Stubs

| File | Description |
|------|-------------|
| src/carpix_images/routers/images.py | GET /v1/images/{brand}/{model}/{year} raises NotImplementedError — intentional RED stub for 06-02 GREEN implementation |
| src/carpix_images/services/image_service.py | get_or_fetch() raises NotImplementedError — intentional RED stub for 06-02 GREEN implementation |

## Threat Flags

No new threat surface introduced. All files are within the established trust model for Phase 6 (see plan threat_model section). The images_router inclusion in main.py is documented in T-06-01.

## Self-Check

- [x] src/carpix_images/routers/images.py exists
- [x] tests/integration/test_images_router.py exists
- [x] 5 unit tests fail RED
- [x] 5 integration tests fail RED
- [x] 27 pre-existing tests pass GREEN
- [x] Commits fcdacda, 840588f, 5280e11 exist

## Self-Check: PASSED
