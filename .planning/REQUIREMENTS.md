# Requirements: Vehicle Image Cache Microservice (carpix-images)

**Defined:** 2026-05-22
**Core Value:** Any vehicle query is answered with an image — cache hit or Wikimedia fetch — never a 500, always a FileResponse or a clean 404.

## v1 Requirements

### API

- [ ] **API-01**: Client can request image via `GET /v1/images/{brand}/{model}/{year}` — cache hit or miss returns `FileResponse` with `Content-Type: image/jpeg`
- [ ] **API-02**: Client receives HTTP 404 with `{"detail": "No image found for this vehicle"}` when Wikimedia returns no results or download fails
- [ ] **API-03**: `GET /health` returns HTTP 200 for process liveness; succeeds even when DB is unreachable
- [ ] **API-04**: Image response includes `X-Cache: HIT` or `X-Cache: MISS` header
- [ ] **API-05**: `GET /health` includes `SELECT 1` DB probe and reports DB connectivity status distinct from process liveness

### Normalization

- [ ] **NORM-01**: Brand and model inputs normalized to canonical keys (lowercase, strip all non-alphanumeric characters) before cache lookup and filesystem path construction; normalization matches parent project's `domain/vehicle_identity.py`

### Cache

- [ ] **CACHE-01**: Cache-hit path: DB hit returns `FileResponse` from local file; Wikimedia is never contacted
- [ ] **CACHE-02**: Cache-miss path: DB miss triggers full 3-step Wikimedia fetch, writes file to disk, inserts DB row, returns `FileResponse`
- [ ] **CACHE-03**: Concurrent requests for the same uncached vehicle serialized via per-key `asyncio.Lock` — prevents duplicate Wikimedia fetches and double-write races
- [ ] **CACHE-04**: If DB reports hit but local file is missing from disk, service re-triggers Wikimedia fetch (self-healing; never returns 500)

### Wikimedia Integration

- [ ] **WIKI-01**: Image fetched via 3-step lookup: search API → imageinfo API → CDN download using `thumburl` field from imageinfo response (never manually constructed)
- [ ] **WIKI-02**: Only JPEG results selected (`mime: image/jpeg` filter on imageinfo); SVG, TIFF, and PNG results skipped
- [ ] **WIKI-03**: Fallback query chain: if `{year} {brand} {model}` returns no JPEG candidate, retry with `{brand} {model}` before returning 404

### Storage

- [ ] **STORE-01**: Images stored at `/images/{brand_key}/{model_key}/{year}/image.jpg`; directories created on first write
- [ ] **STORE-02**: Path traversal guard enforced on all `FileResponse` paths — resolved path must pass `is_relative_to(BASE_IMAGES_DIR)` before serving

### Database

- [ ] **DB-01**: `vehicle_images` table created via Alembic migration with composite primary key `(brand_key, model_key, year)` and columns `local_path`, `source_url`, `file_title`, `cached_at`
- [ ] **DB-02**: Cache repository supports `find()` by composite PK and idempotent `insert()` via `INSERT ... ON CONFLICT DO NOTHING`
- [ ] **DB-03**: PostgreSQL connection pool managed as lifespan-scoped singleton (asyncpg + SQLAlchemy Core); created on startup, closed on shutdown

### Infrastructure

- [ ] **OPS-01**: Multi-stage Dockerfile with non-root `appuser`; `/images` directory created and owned by `appuser` in image
- [ ] **OPS-02**: `docker-compose.yml` with Postgres service, carpix-images service, and named volume mounting `/images` for persistence across restarts
- [ ] **OPS-03**: Container restarts do not re-trigger Wikimedia fetches — DB rows and volume contents survive restart

### Quality

- [ ] **QUAL-01**: Full unit and integration test coverage for all components; Wikimedia HTTP calls stubbed with `respx` (all three hosts); real Postgres via `testcontainers[postgres]`
- [ ] **QUAL-02**: `ruff` + `mypy --strict` clean before every commit

## v2 Requirements

### Observability

- **OBS-01**: Cache statistics endpoint (`GET /v1/stats`) — total cached entries, per-brand counts
- **OBS-02**: Structured logging with request ID, cache result, and Wikimedia fetch duration

### Admin

- **ADMIN-01**: Cache invalidation endpoint (`DELETE /v1/images/{brand}/{model}/{year}`) — removes DB row and local file
- **ADMIN-02**: Batch prefetch endpoint (`POST /v1/prefetch`) — accepts list of vehicles, queues background fetches

## Out of Scope

| Feature | Reason |
|---------|--------|
| Cache TTL / expiry | Images don't change; permanent cache is correct for this use case |
| Local image resize (Pillow) | Wikimedia CDN handles 800px thumbnail server-side; no local processing needed |
| Authentication / API keys | Internal service consumed only by parent carpix app |
| Rate limiting | Wikimedia imposes no enforced limit; internal traffic only |
| Paid image APIs (Getty, Shutterstock) | Project constraint: zero ongoing cost |
| Real-time Wikimedia calls in integration tests | Flaky; Wikimedia HTTP must be stubbed in all automated tests |
| Video or non-JPEG media | Out of domain scope |

## Traceability

Populated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| NORM-01 | — | Pending |
| API-01 | — | Pending |
| API-02 | — | Pending |
| API-03 | — | Pending |
| API-04 | — | Pending |
| API-05 | — | Pending |
| CACHE-01 | — | Pending |
| CACHE-02 | — | Pending |
| CACHE-03 | — | Pending |
| CACHE-04 | — | Pending |
| WIKI-01 | — | Pending |
| WIKI-02 | — | Pending |
| WIKI-03 | — | Pending |
| STORE-01 | — | Pending |
| STORE-02 | — | Pending |
| DB-01 | — | Pending |
| DB-02 | — | Pending |
| DB-03 | — | Pending |
| OPS-01 | — | Pending |
| OPS-02 | — | Pending |
| OPS-03 | — | Pending |
| QUAL-01 | — | Pending |
| QUAL-02 | — | Pending |

**Coverage:**
- v1 requirements: 23 total
- Mapped to phases: 0 (roadmap pending)
- Unmapped: 23 ⚠️

---
*Requirements defined: 2026-05-22*
*Last updated: 2026-05-22 after initial definition*
