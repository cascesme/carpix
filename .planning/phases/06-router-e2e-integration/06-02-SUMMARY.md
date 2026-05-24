---
phase: 06-router-e2e-integration
plan: "02"
subsystem: api
tags: [tdd-green, fastapi, cache-aside, x-cache-header, lifespan-di, asyncpg, test-isolation]
dependency_graph:
  requires:
    - phase: 06-01
      provides: "Router stub + ImageService tuple return stub + 10 failing RED tests"
  provides:
    - "GET /v1/images/{brand}/{model}/{year} returning FileResponse with X-Cache header"
    - "ImageService.get_or_fetch() full cache-aside implementation"
    - "Lifespan DI: httpx.AsyncClient + StorageService + CacheRepository + WikimediaClient + ImageService singleton"
  affects:
    - src/carpix_images/services/image_service.py
    - src/carpix_images/routers/images.py
    - src/carpix_images/main.py
    - tests/integration/test_images_router.py

tech-stack:
  added: []
  patterns:
    - "app.router.lifespan_context(app) for ASGI lifespan management in ASGITransport tests"
    - "asyncio.run() for sync fixture cleanup of async DB state"
    - "DB truncate + shutil.rmtree in module-scoped fixture for test isolation"
    - "cast(ImageService, request.app.state.image_service) for mypy-clean state access"
    - "Per-key asyncio.Lock in ImageService for concurrent request deduplication"

key-files:
  created: []
  modified:
    - src/carpix_images/services/image_service.py
    - src/carpix_images/routers/images.py
    - src/carpix_images/main.py
    - tests/integration/test_images_router.py

key-decisions:
  - "ASGITransport does not trigger ASGI lifespan; must use app.router.lifespan_context(app) explicitly in test fixtures"
  - "scope=function client fixture (not module) avoids event loop scope mismatch with pytest-asyncio asyncio_mode=auto"
  - "Test isolation requires DB TRUNCATE + filesystem cleanup before each module's integration test run"
  - "settings.database_url must be patched in test fixture after postgres_container starts — Settings() is instantiated at import time"
  - "cast(ImageService, request.app.state.image_service) is the mypy-clean way to access typed app state"

patterns-established:
  - "Cache-aside pattern: DB lookup → file_response (hit=True) | Wikimedia fetch → save → insert → file_response (hit=False)"
  - "Self-healing: FileNotFoundError on cached DB entry triggers re-fetch returning cache_hit=False"
  - "X-Cache header injected in router layer (not service layer) — separation of concerns"
  - "http_client.aclose() in lifespan finally block — prevents fd leak (T-06-05 mitigated)"

requirements-completed: [API-01, API-02, API-04, QUAL-01, QUAL-02]

duration: 28min
completed: "2026-05-24"
---

# Phase 06 Plan 02: TDD GREEN — ImageService + Router + Lifespan DI Summary

**Cache-aside ImageService with per-key Lock + X-Cache router + full lifespan DI singleton wiring, 37 tests GREEN, ruff + mypy --strict clean**

## Performance

- **Duration:** ~28 min
- **Started:** 2026-05-24T15:20:00Z
- **Completed:** 2026-05-24T15:48:00Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments

- `ImageService.get_or_fetch()` fully implemented: cache-aside logic with per-key asyncio.Lock, self-healing (FileNotFoundError re-fetch), and HTTPException(404) when Wikimedia returns nothing
- `GET /v1/images/{brand}/{model}/{year}` router implemented: delegates to `app.state.image_service`, unpacks `(response, cache_hit)` tuple, injects `X-Cache: HIT/MISS` header
- Lifespan DI fully wired in `main.py`: `httpx.AsyncClient` + `StorageService` + `CacheRepository` + `WikimediaClient` + `ImageService` singletons, cleaned up in `finally` block
- All 37 tests GREEN: 5 unit (ImageService), 5 integration (images router), 27 pre-existing
- `ruff check src/ tests/` exits 0; `mypy --strict src/` exits 0 (Success: no issues found in 14 source files)

## Task Commits

1. **Task 1: Implement ImageService.get_or_fetch() returning tuple[FileResponse, bool]** - `35df995` (feat)
2. **Task 2: Wire lifespan DI + implement images router with X-Cache header** - `bbdfd34` (feat)
3. **Task 3: Fix test isolation + ruff clean — 37 tests GREEN** - `70a136c` (chore)

## Files Created/Modified

- `src/carpix_images/services/image_service.py` - Full cache-aside implementation: DB lookup, file_response on hit, Wikimedia fetch on miss, per-key Lock for concurrent dedup
- `src/carpix_images/routers/images.py` - GET /v1/images/{brand}/{model}/{year}: calls image_service.get_or_fetch(), injects X-Cache header
- `src/carpix_images/main.py` - Lifespan creates httpx.AsyncClient + full DI chain + ImageService singleton; http_client.aclose() in finally
- `tests/integration/test_images_router.py` - client fixture restructured: lifespan_context per function scope, settings patch, DB truncate + filesystem cleanup for isolation

## Decisions Made

- `ASGITransport` does NOT trigger the ASGI lifespan — must call `app.router.lifespan_context(app)` explicitly in test fixtures. This is not documented clearly in httpx or Starlette, but verified empirically.
- `scope="function"` for the client fixture avoids `RuntimeError: Event loop is closed` caused by `scope="module"` async fixtures conflicting with pytest-asyncio's per-function event loop in `asyncio_mode=auto`.
- `settings.database_url` must be patched directly in test fixture because `Settings()` is instantiated at module import time before `postgres_container` sets the real DB URL.
- `cast(ImageService, request.app.state.image_service)` is used in the router for mypy strict compliance — `State` does not expose typed attribute access.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] ASGITransport does not trigger ASGI lifespan — client fixture restructured**
- **Found during:** Task 2 (integration test run)
- **Issue:** `ASGITransport` in httpx sends only `type: "http"` scope; the FastAPI lifespan (which populates `app.state.image_service`) never ran, causing `AttributeError: 'State' object has no attribute 'image_service'` on every request
- **Fix:** Changed `client` fixture from `scope="module"` (module-shared app + ASGITransport) to `scope="function"` with explicit `async with application.router.lifespan_context(application)` wrapping each test's `AsyncClient` context
- **Files modified:** tests/integration/test_images_router.py
- **Verification:** All 5 integration tests passed after fix
- **Committed in:** bbdfd34 (Task 2 commit)

**2. [Rule 1 - Bug] settings.database_url stale at lifespan startup — patched in fixture**
- **Found during:** Task 2 (integration test run after lifespan fix)
- **Issue:** Pydantic `Settings()` instantiated at module import time captures `DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/testdb` (placeholder). After `postgres_container` fixture sets the real URL in `os.environ`, `settings.database_url` remains stale. Lifespan's `create_async_engine(settings.database_url)` connected to wrong host → `ConnectionRefusedError`
- **Fix:** Added `app_settings.database_url = os.environ["DATABASE_URL"]` in the `client` fixture before `create_app()` — patches the singleton in-place before the lifespan reads it
- **Files modified:** tests/integration/test_images_router.py
- **Verification:** DB connection succeeded; tests progressed to next stage
- **Committed in:** bbdfd34 (Task 2 commit)

**3. [Rule 1 - Bug] Test isolation failure: cache_repository tests pre-populate DB and filesystem**
- **Found during:** Task 3 (full suite `pytest tests/`)
- **Issue:** `test_cache_repository.py` inserts `toyota/corolla/2022` into the DB. A prior full test run also wrote the file to `/tmp/carpix_test_images/toyota/corolla/2022/image.jpg`. Both persisted across the session. When `test_cache_miss` ran, it found DB row + file → returned `X-Cache: HIT` instead of expected `MISS`
- **Fix:** Added `TRUNCATE TABLE vehicle_images` (via `asyncpg.connect` + `asyncio.run()`) and `shutil.rmtree(IMAGES_DIR)` in the `run_migrations` fixture before tests start
- **Files modified:** tests/integration/test_images_router.py
- **Verification:** All 37 tests pass consistently on repeated full-suite runs
- **Committed in:** 70a136c (Task 3 commit)

---

**Total deviations:** 3 auto-fixed (3 Rule 1 — bugs in test infrastructure)
**Impact on plan:** All three fixes were necessary for integration test correctness. No scope creep — all fixes are in `tests/integration/test_images_router.py`. Source files modified exactly as planned.

## Issues Encountered

- Python 3.13 deprecated `asyncio.get_event_loop()` in non-async context → switched to `asyncio.run()` in the sync `run_migrations` fixture
- The unused `import httpx` top-level import in the test file (carried over from 06-01 stub) was caught by ruff F401 and removed

## Known Stubs

None — all stubs from 06-01 are now fully implemented.

## Threat Flags

No new threat surface introduced. All T-06-xx mitigations from the plan's threat model are in place:
- T-06-02: `canonical_key()` at ImageService boundary (implemented)
- T-06-04: `StorageService._validated_path()` in file_response (pre-existing)
- T-06-05: `http_client.aclose()` in lifespan finally block (implemented)
- T-06-06: Three-layer path traversal guard: FastAPI decodes → canonical_key → _validated_path (all in place)

## Self-Check

- [x] `src/carpix_images/services/image_service.py` implements cache-aside logic
- [x] `src/carpix_images/routers/images.py` contains `X-Cache` header injection
- [x] `src/carpix_images/main.py` contains `image_service` in lifespan and `http_client.aclose()`
- [x] `pytest tests/ -v` exits 0 with `37 passed`
- [x] `ruff check src/ tests/` exits 0
- [x] `mypy --strict src/` exits 0 — "Success: no issues found in 14 source files"
- [x] Commits 35df995, bbdfd34, 70a136c exist

## Self-Check: PASSED

## Next Phase Readiness

Phase 06 is complete. The microservice can now:
1. Answer any vehicle image query via `GET /v1/images/{brand}/{model}/{year}`
2. Return `X-Cache: HIT` on repeated requests (filesystem + DB cached)
3. Return `X-Cache: MISS` on first fetch (Wikimedia → save → DB insert)
4. Return `404 {"detail": "No image found for this vehicle"}` when Wikimedia has no result

Ready for Phase 07: Docker containerization and production deployment.

---
*Phase: 06-router-e2e-integration*
*Completed: 2026-05-24*
