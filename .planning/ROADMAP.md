# Roadmap: Vehicle Image Cache Microservice (carpix-images)

## Overview

Build a FastAPI microservice from scratch that answers any vehicle image query — cache hit or Wikimedia fetch — never a 500, always a FileResponse or clean 404. Phases follow a strict dependency chain: foundation first, then storage and database layers, then the Wikimedia client, then the service orchestration that ties it all together, then the API router with full integration tests, and finally containerization for production deployment.

## Phases

**Phase Numbering:**

- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Foundation** - Project scaffolding, normalization logic, and health endpoint skeleton (completed 2026-05-22)
- [x] **Phase 2: Storage Layer** - StorageService with path contract and traversal guard (completed 2026-05-23)
- [x] **Phase 3: Database Layer** - Alembic migration, CacheRepository, and connection pool lifecycle (completed 2026-05-23)
- [x] **Phase 4: Wikimedia Client** - 3-step image fetch with JPEG filter and fallback query chain (completed 2026-05-24)
- [x] **Phase 5: Service Orchestration** - ImageService with cache-aside logic, per-key locking, and self-healing (completed 2026-05-24)
- [x] **Phase 6: Router + E2E Integration** - API endpoints, X-Cache header, and full test suite (completed 2026-05-24)
- [ ] **Phase 7: Containerization** - Dockerfile, docker-compose, and volume persistence

## Phase Details

### Phase 1: Foundation

**Goal**: A runnable FastAPI app skeleton exists with normalization logic and health endpoints wired up
**Depends on**: Nothing (first phase)
**Requirements**: NORM-01, API-03, API-05
**Success Criteria** (what must be TRUE):

  1. `GET /health` returns HTTP 200 with process liveness status even when the database is unreachable
  2. `GET /health` response body includes a DB connectivity probe field (`SELECT 1`) with a value distinct from process liveness
  3. Brand and model strings are normalized to lowercase with all non-alphanumeric characters stripped, matching the behavior of the parent project's `domain/vehicle_identity.py`
  4. The app starts cleanly with `uvicorn main:app` and all routes are discoverable via `/docs`

**Plans**: 2 plans
Plans:
**Wave 1**

- [x] 01-01-PLAN.md — Scaffold project (uv, src-layout pyproject.toml, package dirs, Wave 0 failing test stubs)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 01-02-PLAN.md — Implement canonical_key, config, /health router, app factory; pass ruff + mypy --strict

### Phase 2: Storage Layer

**Goal**: A StorageService can write image bytes to the correct path and serve them safely via FileResponse
**Depends on**: Phase 1
**Requirements**: STORE-01, STORE-02
**Success Criteria** (what must be TRUE):

  1. Image bytes are persisted at `/images/{brand_key}/{model_key}/{year}/image.jpg`; intermediate directories are created automatically on first write
  2. A FileResponse path that resolves outside `/images` (path traversal attempt) is rejected before the response is returned
  3. A valid path that resolves inside `/images` is served without error

**Plans**: 2 plans
Plans:
**Wave 1**

- [x] 02-01-PLAN.md — TDD RED baseline: services package, StorageService stub, 5 failing unit tests, IMAGES_DIR conftest guard

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 02-02-PLAN.md — Implement StorageService.save() + file_response() + traversal guard + Settings.images_dir; all 5 tests GREEN + ruff + mypy clean

### Phase 3: Database Layer

**Goal**: The vehicle_images table exists in Postgres and the CacheRepository can look up and persist cache entries with a managed connection pool
**Depends on**: Phase 2
**Requirements**: DB-01, DB-02, DB-03
**Success Criteria** (what must be TRUE):

  1. Running Alembic migrations creates the `vehicle_images` table with composite primary key `(brand_key, model_key, year)` and all required columns
  2. `CacheRepository.find()` returns a row when one exists for the given composite key and returns nothing when no row exists
  3. `CacheRepository.insert()` is idempotent: a second insert for the same composite key does not raise an error (`ON CONFLICT DO NOTHING`)
  4. The asyncpg/SQLAlchemy connection pool is created on app startup and closed cleanly on shutdown; no leaked connections after shutdown

**Plans**: 2 plans
Plans:
**Wave 1**

- [x] 03-01-PLAN.md — TDD RED baseline: add sqlalchemy + alembic deps, scaffold infrastructure package, write 5 failing integration tests

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 03-02-PLAN.md — Implement Alembic migration + CacheRepository + lifespan pool wiring + testcontainers fixture; all 5 tests GREEN + ruff + mypy clean

### Phase 4: Wikimedia Client

**Goal**: A WikimediaClient can resolve a vehicle query to a downloadable 800px JPEG URL through the 3-step API chain, with JPEG filtering and a fallback query
**Depends on**: Phase 3
**Requirements**: WIKI-01, WIKI-02, WIKI-03
**Success Criteria** (what must be TRUE):

  1. The client fetches `thumburl` from the Wikimedia imageinfo API and uses it directly — no manual URL construction
  2. SVG, TIFF, and PNG results are skipped; only `mime: image/jpeg` candidates are selected
  3. When `{year} {brand} {model}` yields no JPEG candidate, the client retries automatically with `{brand} {model}` before giving up
  4. When both queries yield no result, the client returns a sentinel (None or empty result) without raising an exception

**Plans**: 2 plans
Plans:
**Wave 1**

- [x] 04-01-PLAN.md — TDD RED baseline: move httpx to prod deps, WikimediaClient stub, 6 failing unit tests

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 04-02-PLAN.md — Implement WikimediaClient (find_jpeg_url + _search_first_jpeg); all 6 tests GREEN + ruff + mypy --strict clean

### Phase 5: Service Orchestration

**Goal**: ImageService delivers the cache-aside guarantee — hit returns instantly, miss fetches and stores, concurrent requests for the same key are serialized, and a missing file triggers re-fetch rather than 500
**Depends on**: Phase 4
**Requirements**: CACHE-01, CACHE-02, CACHE-03, CACHE-04
**Success Criteria** (what must be TRUE):

  1. A cache-hit request returns a FileResponse from the local file without making any Wikimedia HTTP calls
  2. A cache-miss request completes the full 3-step Wikimedia fetch, writes the file to disk, inserts a DB row, and returns a FileResponse
  3. Two simultaneous requests for the same uncached vehicle result in exactly one Wikimedia fetch; the second request reuses the result of the first
  4. When the DB reports a hit but the local file is absent, the service re-fetches from Wikimedia and returns a valid FileResponse (no 500)

**Plans**: 2 plans
Plans:
**Wave 1**

- [x] 05-01-PLAN.md — TDD RED baseline: ImageService stub, 5 failing unit tests covering all 4 cache behaviors

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 05-02-PLAN.md — Implement ImageService (cache-aside, asyncio.Lock, self-healing); all 5 tests GREEN + ruff + mypy --strict clean

### Phase 6: Router + E2E Integration

**Goal**: The HTTP API is fully wired with correct status codes, X-Cache headers, and an automated test suite covering all paths with stubbed Wikimedia and real Postgres
**Depends on**: Phase 5
**Requirements**: API-01, API-02, API-04, QUAL-01, QUAL-02
**Success Criteria** (what must be TRUE):

  1. `GET /v1/images/{brand}/{model}/{year}` returns a FileResponse with `Content-Type: image/jpeg` on both cache hit and cache miss
  2. The response includes `X-Cache: HIT` on a cache hit and `X-Cache: MISS` on a cache miss
  3. A vehicle with no Wikimedia results returns HTTP 404 with `{"detail": "No image found for this vehicle"}`
  4. The full test suite passes with Wikimedia HTTP stubbed via `respx` and real Postgres via `testcontainers[postgres]`
  5. `ruff` and `mypy --strict` report zero errors on the entire codebase

**Plans**: 2 plans
Plans:
**Wave 1**

- [x] 06-01-PLAN.md — TDD RED baseline: images router stub, lifespan DI stub, 10 failing unit + integration tests

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 06-02-PLAN.md — Implement ImageService.get_or_fetch(), images router with X-Cache header, lifespan DI wiring; all 37 tests GREEN + ruff + mypy --strict clean

### Phase 7: Containerization

**Goal**: The service runs in Docker with a named volume so cached images and DB rows survive container restarts
**Depends on**: Phase 6
**Requirements**: OPS-01, OPS-02, OPS-03
**Success Criteria** (what must be TRUE):

  1. The multi-stage Dockerfile builds successfully and runs the service as a non-root `appuser`; the `/images` directory exists and is owned by `appuser` inside the image
  2. `docker-compose up` starts the carpix-images service and a Postgres service; the named volume mounts at `/images`
  3. After fetching an image, restarting the container via `docker-compose restart` serves the same image from cache (no Wikimedia re-fetch) — DB rows and volume contents persist

**Plans**: 2 plans
Plans:
**Wave 1**

- [x] 07-01-PLAN.md — Multi-stage Dockerfile with appuser + /images owned by appuser + .dockerignore

**Wave 2** *(blocked on Wave 1 completion)*

- [ ] 07-02-PLAN.md — docker-compose.yml with Postgres service, named volumes, healthcheck-gated startup, and persistence verification checkpoint

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 2/2 | Complete   | 2026-05-22 |
| 2. Storage Layer | 2/2 | Complete   | 2026-05-23 |
| 3. Database Layer | 2/2 | Complete   | 2026-05-23 |
| 4. Wikimedia Client | 2/2 | Complete   | 2026-05-24 |
| 5. Service Orchestration | 2/2 | Complete   | 2026-05-24 |
| 6. Router + E2E Integration | 2/2 | Complete   | 2026-05-24 |
| 7. Containerization | 1/2 | In Progress|  |
