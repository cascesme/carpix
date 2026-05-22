# Architecture Research: Vehicle Image Cache Microservice

**Domain:** FastAPI image caching microservice (cache-aside, Wikimedia upstream)
**Researched:** 2026-05-22
**Confidence:** HIGH — All patterns verified against FastAPI official docs and Context7

---

## Component Map

```
ImageRouter          : HTTP boundary — parse/validate path params, raise 404, return FileResponse
                       Depends on: ImageService

ImageService         : Orchestrate cache-aside logic — check cache → hit or miss path
                       Depends on: CacheRepository, WikimediaClient, StorageService

CacheRepository      : DB read/write for vehicle_images table — SELECT/INSERT only, no update
                       Depends on: asyncpg pool (injected via FastAPI Depends)

WikimediaClient      : Three-step Wikimedia fetch — search API → imageinfo API → CDN download
                       Depends on: httpx.AsyncClient (injected or module-level singleton)

StorageService       : Filesystem I/O — mkdir parents, write bytes via aiofiles, resolve path
                       Depends on: aiofiles, pathlib.Path, configured IMAGES_ROOT

NormalizationUtil    : Pure function — lowercase + strip non-alphanumeric → brand_key/model_key
                       Depends on: nothing (stateless, importable by router and service)

AppFactory (main.py) : Wire lifespan, include router, expose app object for uvicorn/gunicorn
                       Depends on: all of the above (composition root)
```

---

## Data Flow

### Cache Hit

```
GET /v1/images/{brand}/{model}/{year}
  → ImageRouter: normalize(brand, model) → brand_key, model_key
  → ImageService.get_image(brand_key, model_key, year)
    → CacheRepository.find(brand_key, model_key, year) → row with local_path
    → StorageService.exists(local_path) → True
  → ImageRouter: return FileResponse(local_path, media_type="image/jpeg")
```

### Cache Miss

```
GET /v1/images/{brand}/{model}/{year}
  → ImageRouter: normalize(brand, model) → brand_key, model_key
  → ImageService.get_image(brand_key, model_key, year)
    → CacheRepository.find(brand_key, model_key, year) → None
    → WikimediaClient.fetch_thumbnail(brand, model, year)
        Step 1: GET commons.wikimedia.org/w/api.php
                  action=query&list=search&srsearch="{brand} {model} {year}"
                  → file_title (e.g. "File:BYD_Seal_2023.jpg")
        Step 2: GET commons.wikimedia.org/w/api.php
                  action=query&titles={file_title}&prop=imageinfo&iiprop=url
                  → canonical_url (e.g. https://upload.wikimedia.org/wikipedia/commons/a/ab/BYD_Seal_2023.jpg)
        Step 3: Derive thumbnail URL by inserting /thumb/ and appending /800px-{filename}
                  GET {thumbnail_url} → image bytes
      → WikimediaClient returns: ImageResult(bytes, source_url, file_title)
         on no results or download failure → raises WikimediaNotFoundError
    → StorageService.write(brand_key, model_key, year, bytes)
        path = /images/{brand_key}/{model_key}/{year}/image.jpg
        mkdir -p, aiofiles.open write
      → returns local_path: str
    → CacheRepository.insert(brand_key, model_key, year, local_path, source_url, file_title)
  → ImageRouter: return FileResponse(local_path, media_type="image/jpeg")

WikimediaNotFoundError (any step) → ImageRouter raises HTTPException(404, "No image found for this vehicle")
```

### Health Check

```
GET /health
  → HealthRouter: return {"status": "ok"}  (no DB probe needed for liveness)
```

---

## Layer Structure

```
carpix-images/
├── app/
│   ├── main.py                  # AppFactory: lifespan, include_router, app object
│   ├── config.py                # Pydantic Settings: DB_URL, IMAGES_ROOT, USER_AGENT
│   │
│   ├── api/
│   │   └── v1/
│   │       ├── router.py        # include sub-routers, prefix="/v1"
│   │       ├── images.py        # GET /images/{brand}/{model}/{year}
│   │       └── health.py        # GET /health
│   │
│   ├── domain/
│   │   ├── normalization.py     # normalize(s: str) -> str  (pure, matches parent)
│   │   └── models.py            # CachedImage dataclass, ImageResult dataclass
│   │
│   ├── services/
│   │   └── image_service.py     # ImageService: orchestrates cache-aside
│   │
│   ├── repositories/
│   │   └── cache_repository.py  # CacheRepository: asyncpg SELECT/INSERT
│   │
│   ├── clients/
│   │   └── wikimedia.py         # WikimediaClient: 3-step fetch, WikimediaNotFoundError
│   │
│   ├── storage/
│   │   └── filesystem.py        # StorageService: aiofiles write, pathlib path resolution
│   │
│   └── dependencies.py          # FastAPI Depends factories: get_db_pool, get_image_service
│
├── tests/
│   ├── unit/
│   │   ├── test_normalization.py
│   │   ├── test_wikimedia_client.py   # httpx mock transport
│   │   ├── test_storage_service.py    # tmp_path fixture
│   │   └── test_image_service.py      # mock repo + client + storage
│   └── integration/
│       ├── conftest.py                # testcontainers postgres, tmp_path IMAGES_ROOT
│       └── test_images_endpoint.py    # httpx AsyncClient, stub Wikimedia transport
│
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml                     # ruff, mypy, pytest config
└── alembic/                           # migration: CREATE TABLE vehicle_images
```

**Rationale for this layout:**
- `domain/` holds zero-dependency pure logic; safe to import anywhere
- `services/` holds the single orchestration class; testable by injecting fakes
- `repositories/` and `clients/` are I/O adapters; easy to swap or stub
- `storage/` isolates filesystem concerns from service logic
- `dependencies.py` is the only place FastAPI `Depends` wiring lives; keeps layers clean

---

## Build Order

### Phase 1: Foundation (no external I/O)
- `config.py` — Pydantic Settings (DB_URL, IMAGES_ROOT, USER_AGENT)
- `domain/normalization.py` — pure normalize function + unit tests
- `domain/models.py` — CachedImage and ImageResult dataclasses
- `main.py` skeleton — lifespan stub, health router wired, app boots

**Gate:** `GET /health` returns 200; ruff + mypy clean; normalization tests pass.

### Phase 2: Storage layer
- `storage/filesystem.py` — StorageService: mkdir, aiofiles write, path resolver
- Unit tests with `tmp_path` — no DB, no network

**Gate:** StorageService unit tests pass; paths resolve to `/images/{b}/{m}/{y}/image.jpg`.

### Phase 3: Database layer
- `alembic/` migration — CREATE TABLE vehicle_images with composite PK
- `repositories/cache_repository.py` — CacheRepository: find() + insert() via asyncpg pool
- `dependencies.py` — `get_db_pool` lifespan-attached pool
- Unit tests with asyncpg mock or real postgres via testcontainers

**Gate:** CacheRepository tests pass against real Postgres container; SELECT/INSERT round-trip verified.

### Phase 4: Wikimedia client
- `clients/wikimedia.py` — WikimediaClient: 3-step fetch, WikimediaNotFoundError
- Unit tests with `httpx.MockTransport` — all three HTTP calls stubbed; 0-result and download-fail cases covered

**Gate:** All Wikimedia unit tests pass; no live HTTP calls in test suite.

### Phase 5: Service orchestration
- `services/image_service.py` — ImageService: cache-aside using injected repo + client + storage
- Unit tests — fake repo (hit/miss), fake client (result/notfound), fake storage; assert correct path taken

**Gate:** Cache-hit and cache-miss paths verified without any I/O; error propagation to HTTPException confirmed.

### Phase 6: Router and end-to-end
- `api/v1/images.py` — path params, normalize call, service call, FileResponse / HTTPException
- `dependencies.py` — `get_image_service` wiring final Depends chain
- Integration tests — httpx.AsyncClient against full app; Wikimedia stubbed; real Postgres via testcontainers; real tmp filesystem

**Gate:** Full endpoint tests pass (hit, miss, 404 on no results, 404 on download failure); ruff + mypy clean.

### Phase 7: Containerization
- `Dockerfile` — multi-stage, non-root user, `/images` volume mount point created
- `docker-compose.yml` — postgres service, carpix-images service, named volume for `/images`

**Gate:** `docker compose up` serves a real request; volume survives container restart.

---

## Integration Points

### ImageRouter → ImageService
- Call: `await service.get_image(brand_key, model_key, year) -> str` (local_path)
- Raises: `WikimediaNotFoundError` caught in router → `HTTPException(404, "No image found for this vehicle")`
- Returns: `FileResponse(local_path, media_type="image/jpeg")`

### ImageService → CacheRepository
- `await repo.find(brand_key, model_key, year) -> CachedImage | None`
- `await repo.insert(brand_key, model_key, year, local_path, source_url, file_title) -> None`
- Injected via `Depends(get_cache_repository)` — pool from app lifespan state

### ImageService → WikimediaClient
- `await client.fetch_thumbnail(brand, model, year) -> ImageResult`
- `ImageResult` carries: `bytes: bytes`, `source_url: str`, `file_title: str`
- Raises: `WikimediaNotFoundError` on search no-results or CDN download failure
- Client holds a module-level `httpx.AsyncClient` created in lifespan (reuse connection pool)

### ImageService → StorageService
- `await storage.write(brand_key, model_key, year, data: bytes) -> str` (absolute path)
- `await storage.exists(path: str) -> bool` (used to verify file integrity on cache-hit)
- Pure filesystem; no FastAPI knowledge

### AppFactory lifespan → asyncpg pool
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.db_pool = await asyncpg.create_pool(settings.DB_URL)
    app.state.http_client = httpx.AsyncClient(headers={"User-Agent": settings.USER_AGENT})
    yield
    await app.state.db_pool.close()
    await app.state.http_client.aclose()
```
- Both pool and HTTP client are created once at startup, closed at shutdown
- Injected into request-scoped dependencies via `request.app.state`

### Docker volume → filesystem
- Volume: `carpix_images:/images` mounted read-write in both carpix and carpix-images containers
- StorageService.IMAGES_ROOT configured via `IMAGES_ROOT=/images` env var
- Path contract: `/images/{brand_key}/{model_key}/{year}/image.jpg` — never changes after first write

---

## Key Architectural Decisions

| Decision | Rationale |
|----------|-----------|
| Service layer owns cache-aside logic, not the router | Router stays thin; service is independently testable with fakes |
| WikimediaNotFoundError as domain exception, not HTTPException | Client layer has no FastAPI knowledge; router translates |
| asyncpg pool in lifespan state, not module global | Enables clean startup/shutdown and pool injection in tests via app override |
| httpx.AsyncClient in lifespan state (not per-request) | Connection pool reuse; follows httpx best practice |
| aiofiles for all filesystem writes | Avoids blocking the event loop under concurrent requests |
| No ORM — raw asyncpg SQL | Table is append-mostly with composite PK lookup; ORM adds no value here |
| Normalization in domain/, imported by both router and service | Single source of truth; matches parent project's `domain/vehicle_identity.py` logic |
| Stub Wikimedia with httpx.MockTransport, not responses/respx | Stays within the httpx ecosystem; no additional test dependencies |

---

## Sources

- FastAPI lifespan pattern: https://github.com/fastapi/fastapi/blob/master/docs/en/docs/release-notes.md (Context7 /fastapi/fastapi)
- FastAPI FileResponse: https://github.com/fastapi/fastapi/blob/master/docs/en/docs/advanced/custom-response.md (Context7 /fastapi/fastapi)
- FastAPI APIRouter: https://github.com/fastapi/fastapi/blob/master/docs/en/docs/tutorial/bigger-applications.md (Context7 /fastapi/fastapi)
- FastAPI HTTPException: https://github.com/fastapi/fastapi/blob/master/docs/en/docs/tutorial/handling-errors.md (Context7 /fastapi/fastapi)
- asyncpg connection pool: https://context7.com/magicstack/asyncpg/llms.txt (Context7 /magicstack/asyncpg)
- httpx async streaming: https://github.com/encode/httpx/blob/master/docs/async.md (Context7 /encode/httpx)
- Wikimedia imageinfo API: https://www.mediawiki.org/wiki/API:Imageinfo
- Testcontainers + FastAPI + asyncpg integration test pattern: https://lealre.github.io/fastapi-testcontainer-asyncpg/
- FastAPI layered architecture: https://dev.to/markoulis/layered-architecture-dependency-injection-a-recipe-for-clean-and-testable-fastapi-code-3ioo
