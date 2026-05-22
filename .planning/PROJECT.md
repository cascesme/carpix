# Vehicle Image Cache Microservice (carpix-images)

## What This Is

A standalone FastAPI microservice that serves car images by brand, model, and year. On the first request for a given vehicle, it fetches a CC-licensed image from Wikimedia Commons, saves an 800px thumbnail locally, and returns it — all subsequent requests for that vehicle are served directly from the filesystem cache. Deployed as a sibling Docker container alongside the parent carpix application.

## Core Value

Any vehicle query is answered with an image — cache hit or Wikimedia fetch — never a 500, always a FileResponse or a clean 404.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Client can request an image by brand, model, and year via `GET /v1/images/{brand}/{model}/{year}`
- [ ] Cache hit returns the locally stored JPEG immediately (FileResponse)
- [ ] Cache miss fetches from Wikimedia Commons (search → resolve → download 800px thumbnail), stores locally, inserts DB row, then returns FileResponse
- [ ] Wikimedia no-results or download failure returns 404 with `{"detail": "No image found for this vehicle"}`
- [ ] Input brand/model are normalized to canonical keys (lowercase, strip non-alphanumeric) before cache lookup
- [ ] Cached images persist across container restarts via Docker volume mount at `/images`
- [ ] `GET /health` returns service liveness status
- [ ] Full unit + integration test coverage (Wikimedia HTTP stubbed, real Postgres)
- [ ] Ruff + mypy clean codebase

### Out of Scope

- Cache invalidation / TTL — images don't change, cache is permanent
- Image resize locally — Wikimedia CDN handles 800px thumbnail server-side
- Authentication / API keys — internal service, no auth needed
- Rate limiting — Wikimedia imposes no enforced limit
- Mobile app or UI — API only
- Paid image APIs — project constraint: zero cost

## Context

- **Parent project**: carpix (vehicle comparison/discovery app at `/home/ccastro/Projects/carpix`)
- **Deployment**: Sibling Docker container; carpix calls this service for car imagery
- **Image source**: Wikimedia Commons (CC-licensed, no API key required)
- **Wikimedia CDN pattern**: insert `/thumb/` after `/commons/` and append `/800px-{filename}` — no local resize needed
- **Normalization**: lowercase + strip all non-alphanumeric chars; must match parent project logic in `domain/vehicle_identity.py`
- **Validated Wikimedia query**: "BYD Seal 2023" returns 66 results — API works
- **DB table**: `vehicle_images` with composite PK `(brand_key, model_key, year)`, tracks `local_path`, `source_url`, `file_title`, `cached_at`

## Constraints

- **Tech stack**: FastAPI (Python, async) — mirrors parent project
- **Storage**: Local filesystem at `/images/{brand_key}/{model_key}/{year}/image.jpg`
- **Database**: PostgreSQL — same engine as parent project
- **Containerization**: Docker + docker-compose with `/images` volume for persistence
- **Image width**: 800px via Wikimedia CDN thumbnail pattern only (no PIL/Pillow resize)
- **Error handling**: Extraction failures always 404, never 500
- **Development**: SOLID principles, TDD (tests first), ruff + mypy clean before commit

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Wikimedia Commons as image source | CC-licensed, zero cost, no API key, validated working | — Pending |
| PostgreSQL for cache tracking | Mirror parent project; tracks metadata (source URL, file title, timestamps) | — Pending |
| 800px via CDN pattern, no local resize | Wikimedia handles thumbnail server-side, ~200KB result, zero processing overhead | — Pending |
| Stub Wikimedia HTTP in integration tests | Prevent flaky tests from network dependency; real Postgres via compose | — Pending |
| Sibling Docker service (separate repo) | Clean separation from parent; independent deploy and scale | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-22 after initialization*
