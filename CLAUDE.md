<!-- GSD:project-start source:PROJECT.md -->
## Project

**Vehicle Image Cache Microservice (carpix-images)**

A standalone FastAPI microservice that serves car images by brand, model, and year. On the first request for a given vehicle, it fetches a CC-licensed image from Wikimedia Commons, saves an 800px thumbnail locally, and returns it — all subsequent requests for that vehicle are served directly from the filesystem cache. Deployed as a sibling Docker container alongside the parent carpix application.

**Core Value:** Any vehicle query is answered with an image — cache hit or Wikimedia fetch — never a 500, always a FileResponse or a clean 404.

### Constraints

- **Tech stack**: FastAPI (Python, async) — mirrors parent project
- **Storage**: Local filesystem at `/images/{brand_key}/{model_key}/{year}/image.jpg`
- **Database**: PostgreSQL — same engine as parent project
- **Containerization**: Docker + docker-compose with `/images` volume for persistence
- **Image width**: 800px via Wikimedia CDN thumbnail pattern only (no PIL/Pillow resize)
- **Error handling**: Extraction failures always 404, never 500
- **Development**: SOLID principles, TDD (tests first), ruff + mypy clean before commit
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack

| Layer | Library | Why |
|---|---|---|
| HTTP framework | FastAPI | async-native, mirrors parent project |
| DB driver | asyncpg 0.31+ via SQLAlchemy 2.0 async | pure-async, no thread-pool adapter; bottleneck is Wikimedia fetch not DB |
| HTTP client | httpx | async/await native; respx mocks its transport cleanly |
| Async file I/O | anyio | used by StorageService for async mkdir/write |
| Migrations | Alembic | async-compatible; runs `alembic upgrade head` at container start |
| Testing | pytest-asyncio + respx + testcontainers[postgres] | async-native, no mock leakage, real DB in CI |
| Lint/format | ruff | replaces flake8 + isort + pyupgrade |
| Type checking | mypy (strict) | full type coverage enforced |
| Packaging | uv + hatchling | fast installs, lock file committed |

**Do not use:** Pillow/PIL (resize via Wikimedia CDN `iiurlwidth` param instead), requests, psycopg2/3, SQLAlchemy ORM (raw `text()` queries only).
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

### Key normalization
`canonical_key(value)` in `domain/normalize.py` strips all non-alphanumeric chars and lowercases. Use it on brand and model before any cache lookup or storage path construction. `"DM-i"`, `"DMi"`, and `"DM i"` all map to `"dmi"`.

### Dependency injection
Services receive collaborators via constructor. Routers retrieve them from `request.app.state` with an explicit `cast()`. No global singletons outside `main.py` lifespan.

### Error handling
All fetch/extraction failures raise `HTTPException(status_code=404)`. Never raise 500 — if Wikimedia returns nothing or the download fails, 404 is the contract.

### DB access
Raw SQL via `sqlalchemy.text()` only — no ORM, no mapped classes. `CacheRepository` uses `dataclass` for `CacheEntry`. Upsert on conflict: `ON CONFLICT (brand_key, model_key, year) DO UPDATE`.

### File I/O
`StorageService` uses `anyio.Path` for async writes. Always validates resolved path is under `_base` to prevent path traversal.

### Concurrency
`ImageService` holds a `dict[tuple, asyncio.Lock]` keyed by `(brand_key, model_key, year)` to coalesce concurrent fetches for the same vehicle.

### Response header
Set `X-Cache: HIT` or `X-Cache: MISS` on every image response.

### Module-level imports
All source files start with `from __future__ import annotations`.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

```
src/carpix_images/
├── main.py                        # App factory + lifespan wiring (engine, http_client, services)
├── config.py                      # Pydantic-settings (DATABASE_URL, IMAGES_DIR)
├── domain/
│   └── normalize.py               # canonical_key() — pure logic, no I/O
├── infrastructure/
│   └── cache_repository.py        # CacheRepository — PostgreSQL read/write via asyncpg
├── services/
│   ├── image_service.py           # ImageService — orchestrates fetch/cache/serve
│   ├── storage.py                 # StorageService — async filesystem save + FileResponse
│   └── wikimedia.py               # WikimediaClient — Wikimedia Commons API search
└── routers/
    ├── health.py                  # GET /health
    └── images.py                  # GET /v1/images/{brand}/{model}/{year}
```

### Request flow

```
Router → ImageService.get_or_fetch()
           ├── canonical_key(brand), canonical_key(model)
           ├── acquire per-vehicle asyncio.Lock
           ├── CacheRepository.find() → hit → StorageService.file_response()
           └── miss → WikimediaClient.find_jpeg_url()
                        └── httpx GET 800px thumb → StorageService.save()
                              └── CacheRepository.insert() → StorageService.file_response()
```

### DB schema

Table `vehicle_images`, PK `(brand_key, model_key, year)`:

| Column | Type |
|---|---|
| brand_key | text |
| model_key | text |
| year | integer |
| local_path | text |
| source_url | text |
| file_title | text |
| cached_at | timestamptz (server default now()) |
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
