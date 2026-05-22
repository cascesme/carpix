# Pitfalls Research: Vehicle Image Cache Microservice

**Domain:** FastAPI image proxy/cache microservice with Wikimedia Commons + PostgreSQL + local filesystem
**Researched:** 2026-05-22
**Overall confidence:** HIGH (all major risk areas verified against official sources or multiple independent sources)

---

## Critical Pitfalls (Will Break Production)

### Wikimedia CDN Thumbnail URL Uses MD5 Hash Subdirectories — Not a Simple /thumb/ Insertion

**What goes wrong:** The PROJECT.md states the pattern as "insert `/thumb/` after `/commons/` and append `/800px-{filename}`." This is incomplete. The actual CDN URL is `https://upload.wikimedia.org/wikipedia/commons/thumb/{a}/{ab}/{filename}/{width}px-{filename}` where `{a}` is the first character of the MD5 hash of the normalized filename and `{ab}` is the first two characters. Without the hash subdirectories, every CDN download request will 404.

**Why it happens:** The two-directory hash structure exists to prevent directories from containing too many files (Wikimedia FAQ). The simplified URL pattern that omits hash subdirectories is a common misreading of the pattern — it only works when you already have a canonical URL from the imageinfo API response.

**Consequence:** All cache-miss fetches return 404 from the CDN, so the service returns 404 for every new vehicle — looks correct in tests if tests use a hardcoded stub URL, but fails immediately in production.

**Prevention:** Do not construct CDN thumbnail URLs manually. Always use the `thumburl` property returned by `action=query&prop=imageinfo&iiprop=url|thumburl&iiurlwidth=800` instead of computing it yourself. The imageinfo API returns the correct pre-hashed URL; that is the only reliable source. Note: since a recent API change (tracked in Wikimedia phabricator T109125), the returned thumbnail may be equal-to-or-larger than the requested `iiurlwidth`, not necessarily exact — always follow the returned URL.

**Warning signs:** CDN download step returns HTTP 404 even when the API search and imageinfo steps both succeed. Manual curl of a constructed URL to upload.wikimedia.org returns 404.

**Phase:** Phase 1 (Wikimedia integration) — verify against live API before writing the download step.

---

### SVG Files Produce PNG Thumbnails — Breaking the .jpg Extension Assumption

**What goes wrong:** Many Wikimedia Commons car images are SVG files (especially manufacturer logos, brand insignia). When you request a thumbnail for an SVG file, the CDN serves a `.png` file at a URL like `800px-Filename.svg.png`, not `800px-Filename.svg`. If the service saves the file as `image.jpg` without verifying the actual content type, the stored file contains PNG bytes but has a `.jpg` extension, which confuses clients.

**Why it happens:** MediaWiki converts SVG to PNG for thumbnails automatically. The `thumburl` returned from the imageinfo API reflects this — it ends in `.svg.png`. Downstream code that assumes `.jpg` breaks silently.

**Consequence:** FileResponse for an SVG-sourced file returns data with incorrect MIME type, causing browser rendering failures. Some clients reject it.

**Prevention:** Inspect the `thumburl` from the imageinfo API response before downloading. If the URL ends in `.svg.png` or the `thumbmime` property indicates `image/png`, either (a) skip SVG results and continue searching for a JPEG result, or (b) store the file with the correct extension and return the correct content-type. For a vehicle image cache the simplest approach is to skip SVG results — filter search results to those with `mime: image/jpeg` or `image/png` from the imageinfo response.

**Warning signs:** FileResponse returns images that fail to display in browser. `thumburl` from API response ends in `.svg.png`. Stored files at `/images/.../image.jpg` have PNG magic bytes.

**Phase:** Phase 1 (Wikimedia integration) — add MIME type filter to the imageinfo result selection step.

---

### Path Traversal via Brand/Model URL Parameters to FileResponse

**What goes wrong:** `GET /v1/images/{brand}/{model}/{year}` takes URL path segments that are used (after normalization) to construct a filesystem path like `/images/{brand_key}/{model_key}/{year}/image.jpg`. If normalization is insufficient, an attacker can pass `../../../etc/passwd` as a segment. FastAPI's `FileResponse(path)` does not validate that the resolved path stays within the allowed directory.

**Why it happens:** URL path parameters are decoded by the ASGI server before reaching route handlers. The normalization (lowercase + strip non-alphanumeric) must happen before the path is constructed, not after. A parameter like `..%2F..%2Fetc` decoded and then normalized may still escape if the normalization regex only strips after decoding.

**Consequence:** Arbitrary local file read and exfiltration via HTTP. FileResponse will serve any readable file on the container filesystem.

**Prevention:** After constructing the full `Path` object, call `path.resolve()` and assert that it is relative to the base images directory using `resolved_path.is_relative_to(BASE_IMAGES_DIR)`. Raise `HTTPException(404)` if the check fails. This is a two-line guard but must not be omitted. The normalization regex (strip non-alphanumeric) already eliminates `/` and `.` — rely on that normalization being applied before path construction, then verify with `is_relative_to` as a belt-and-suspenders check.

**Warning signs:** No `is_relative_to` check present in the file-serving code path. Tests do not include a path traversal test case.

**Phase:** Phase 1 (core endpoint) — add guard when first implementing file serving; add a test covering `../` input.

---

### httpx AsyncClient Created Per-Request Instead of at Lifespan

**What goes wrong:** Every `GET /v1/images/...` call creates a new `async with httpx.AsyncClient() as client:` context manager that opens TCP connections, negotiates TLS, and then tears them all down at the end of the request. Under any load, this causes connection exhaustion, slow tail latency, and "Too many open files" errors.

**Why it happens:** The `async with` pattern looks natural for resource management, and the per-request approach works correctly for a single request — it only fails under concurrent load or in any performance test.

**Consequence:** Under even modest concurrency (10+ simultaneous cache-miss requests) the service degrades severely. TLS handshake overhead turns a 200ms Wikimedia fetch into 700ms+.

**Prevention:** Create exactly one `httpx.AsyncClient` in the FastAPI lifespan context manager and store it on `app.state.http_client`. Inject it as a dependency via `request.app.state.http_client` or a `Depends()` function. Close it (`await client.aclose()`) in the lifespan teardown.

**Warning signs:** `AsyncClient()` appears inside any route handler or service method rather than in `lifespan`. No `app.state` usage for the HTTP client.

**Phase:** Phase 1 (service setup) — establish the lifespan pattern before writing the first route.

---

### SQLAlchemy Async MissingGreenlet — Lazy Loading in Async Context

**What goes wrong:** SQLAlchemy async sessions do not support lazy loading. Any ORM relationship or deferred column accessed outside of the original `await session.execute()` call raises `sqlalchemy.exc.MissingGreenlet: greenlet_spawn has not been called`. This is a runtime error that does not appear until the specific code path is hit.

**Why it happens:** SQLAlchemy's async layer uses greenlets internally. Accessing an attribute that requires an additional DB query (lazy load) outside an active greenlet context raises this error. It is easy to introduce by accessing a relationship attribute on a returned ORM object after the session has already yielded control.

**Consequence:** Any route that touches lazy-loaded ORM attributes crashes at runtime with a 500.

**Prevention:** This project uses a simple `vehicle_images` table with no relationships, so the risk is low but still present. Use `mapped_column()` (not `Column()`) for all columns to retain full typing and avoid the SQLAlchemy 2.0 mypy plugin (which is deprecated for 2.0). Use `AsyncSession` (not `Session`) everywhere. Use `create_async_engine()` (not `create_engine()`). If ORM objects are returned from route handlers, use `selectinload()` or `joinedload()` at query time for any associations rather than accessing them later.

**Warning signs:** `create_engine` used instead of `create_async_engine`. `Session` dependency instead of `AsyncSession`. Any `.relationship()` defined without `lazy="raise"` as a safety net.

**Phase:** Phase 1 (database layer) — set up async engine and session factory before writing any route logic.

---

## Common Mistakes (Will Slow Development)

### Wikimedia API Search Returning Empty Results for Valid Vehicles

**What goes wrong:** The Wikimedia Commons `action=query&list=search` API returns zero results for valid vehicles when the query string does not match the file naming conventions used in Commons. For example, searching "Toyota Camry 2020" may return nothing while "Toyota Camry" or "Camry 2020" returns results. The API also returns a `searchinfo.totalhits: 0` field when there are no results — code that does not check this before accessing `query.search[0]` will raise a `KeyError` or `IndexError`.

**Why it happens:** Wikimedia Commons file names are user-contributed and have no canonical naming standard for vehicles. Query matching is exact-ish against file names and descriptions. The validated query in the spec ("BYD Seal 2023") works for that specific make/model/year combination but the pattern does not generalize.

**Consequence:** High 404 rate in production for vehicles that do exist in Commons under a different query. Brittle query logic that needs per-make adjustments over time.

**Prevention:** Make the query construction pluggable and implement a fallback chain: try `{brand} {model} {year}` first, then `{brand} {model}`, log which tier matched. Guard all list indexing: check `len(results) > 0` before `results[0]`. Return 404 cleanly when all tiers are exhausted. Never raise `KeyError` or `IndexError` — treat any missing field as "no result."

**Warning signs:** Direct `response["query"]["search"][0]` without length check. Single fixed query template. No fallback query logic.

**Phase:** Phase 1 (Wikimedia integration) + Phase 2 (quality pass).

---

### Filesystem Race Condition on Concurrent Cache-Miss Requests for the Same Vehicle

**What goes wrong:** Two simultaneous requests for `GET /v1/images/toyota/camry/2020` both find no cache entry in the DB (cache miss), both start a Wikimedia fetch, both download the image, both try to write `/images/toyota/camry/2020/image.jpg`, and both try to insert a row into `vehicle_images`. One insert succeeds, the other raises a unique-constraint violation — or both writes corrupt the file if non-atomic.

**Why it happens:** The cache-aside check-then-act is not atomic. Between the DB read (miss) and the DB write (insert after download), another coroutine can complete the same sequence.

**Consequence:** Occasional `IntegrityError` on the DB insert (not catastrophic if caught), but also potential partial-file corruption if two async writes interleave. In a high-traffic service this occurs frequently; for a low-traffic internal service it is an occasional background error.

**Prevention:** Two strategies (pick one or combine): (1) In-process asyncio lock keyed on the normalized vehicle tuple (`brand_key + model_key + year`) — first coroutine acquires, fetches, stores; second coroutine waits, then finds the cache hit. (2) "INSERT ... ON CONFLICT DO NOTHING" on the DB row plus write-to-temp-then-rename for the file (atomic on POSIX). The rename approach is: write to `image.jpg.tmp`, then `os.rename()` which is atomic on the same filesystem. For simplicity in a single-worker service, the per-key asyncio lock is the cleanest solution.

**Warning signs:** No lock or deduplication around the DB read → download → DB write sequence. No `os.rename` or similar atomic write pattern. No `ON CONFLICT` clause on the DB insert.

**Phase:** Phase 1 (cache logic) — design the deduplication pattern before implementing the cache-miss path.

---

### Docker Volume Mount Permissions — Container Cannot Write to /images

**What goes wrong:** When the Docker volume is mounted at `/images`, the directory may be owned by `root:root` with permissions `755`, but the FastAPI process inside the container runs as a non-root user. The service starts cleanly, passes the health check, but every cache-miss attempt fails with `PermissionError: [Errno 13] Permission denied: '/images/...'`, returning a 500.

**Why it happens:** On Linux, Docker bind mounts preserve host directory ownership (UID/GID numbers). If the host directory was created by root, and the container user is UID 1000, writes fail. Named volumes have the same issue when the volume is first initialized.

**Consequence:** Silent startup — service appears healthy, but all cache writes fail. Errors only appear at cache-miss time, which may not be caught in a health check.

**Prevention:** In `docker-compose.yml`, either (a) ensure the bind-mount host directory is `chown`-ed to match the container's user UID before starting, or (b) run an `entrypoint.sh` that `chown`s `/images` to the application user using an initial root step then drops privileges via `gosu` or `su-exec`. The simplest approach for a sibling container: create the volume as a named Docker volume (not a host bind mount) and set directory permissions in the Dockerfile with `RUN mkdir -p /images && chown appuser:appuser /images`.

**Warning signs:** `RUN useradd` in Dockerfile but no corresponding directory ownership fix for `/images`. Volume defined as a bind mount without host-side setup documentation. No write test in the health check.

**Phase:** Phase 2 (Docker/deployment) — test by running the container locally as the non-root user before considering it production-ready.

---

### mypy Strict Mode and SQLAlchemy 2.0 — Plugin Is Deprecated

**What goes wrong:** SQLAlchemy 2.0's mypy plugin (`sqlalchemy.ext.mypy.plugin`) works only up to mypy 1.10.x and is broken in mypy 1.11+. Projects that add `plugins = sqlalchemy.ext.mypy.plugin` to `mypy.ini` get errors with recent mypy versions and miss type checking on ORM models. Additionally, using `Column()` instead of `mapped_column()` with `Mapped[...]` annotations loses type inference entirely.

**Why it happens:** SQLAlchemy 2.0 replaced the mypy plugin approach with native PEP-484 typing via `Mapped[T]` and `mapped_column()`. The plugin is a legacy compatibility shim.

**Consequence:** Either mypy passes but silently skips ORM model type checking (plugin disabled), or mypy errors block CI (plugin broken on new mypy).

**Prevention:** Do not use the SQLAlchemy mypy plugin. Use SQLAlchemy 2.0 native typing exclusively: `class VehicleImage(Base): brand_key: Mapped[str] = mapped_column(String, primary_key=True)`. This is fully mypy-compatible without any plugin. Also use `async_sessionmaker[AsyncSession]` (not `sessionmaker`) and annotate the session dependency return type as `AsyncGenerator[AsyncSession, None]` to keep mypy strict mode happy.

**Warning signs:** `plugins = sqlalchemy.ext.mypy.plugin` in mypy config. `Column()` usage in model definitions. `Any` type annotations on session factory variables.

**Phase:** Phase 1 (database model) — set up the ORM model with native typing from the start to avoid a later mypy cleanup pass.

---

### Wikimedia CDN Returns Non-JPEG Content Types for Vehicle Searches

**What goes wrong:** A Wikimedia Commons search for a vehicle can return results that are not photographs: diagrams, brochures, logos, infographics, or technical drawings. Some of these are SVG (converts to PNG thumbnail), some are TIFF or WebP. Treating the first search result as a JPEG photo and serving it as `image/jpeg` produces broken images for clients that expect a car photo.

**Why it happens:** Wikimedia Commons is a general media repository. Vehicle searches return all file types associated with the search term, not just JPEG photos.

**Prevention:** Filter imageinfo results: only accept files where `mime` is `image/jpeg` or where `thumbmime` is `image/jpeg`. Skip SVG, TIFF, WebP, and any `image/png` (unless the fallback chain exhausts JPEG candidates). If no JPEG result is found after filtering across all search results, return 404.

**Warning signs:** No MIME type filtering before selecting a result. Serving all files with `media_type="image/jpeg"` regardless of actual content.

**Phase:** Phase 1 (Wikimedia integration) — implement MIME filter as part of the result selection step.

---

### asyncpg Prepared Statement Cache Errors with PgBouncer

**What goes wrong:** If the PostgreSQL connection is fronted by PgBouncer in transaction pooling mode (which is a common deployment pattern when PostgreSQL is a shared resource), asyncpg's default prepared statement cache causes `DuplicatePreparedStatementError` errors because PgBouncer routes each transaction to a potentially different backend connection, which does not have the prepared statement cached.

**Why it happens:** asyncpg caches prepared statements per-connection (default cache size: 100). PgBouncer transaction mode reassigns connections between transactions, so a prepared statement prepared on connection A is not visible on connection B when the next transaction executes.

**Consequence:** Random `DuplicatePreparedStatementError` or `CachedPlanMustNotChangeResultType` errors in production under concurrent load.

**Prevention:** For this project, no PgBouncer is used (direct asyncpg to PostgreSQL in a sibling container). Document this assumption in the service's `README` and `docker-compose.yml`. If PgBouncer is ever introduced, add `prepared_statement_cache_size=0` to the asyncpg connect arguments in the engine URL. Early detection: if you see prepared statement errors in tests, the test database connection is going through a pooler.

**Warning signs:** Connection URL contains a port associated with PgBouncer (typically 6432). `DuplicatePreparedStatementError` in logs. Using a managed PostgreSQL service that proxies connections.

**Phase:** Informational for Phase 1/2 — confirm direct connection in compose file.

---

## Testing Pitfalls

### respx Mocks Not Applied to the Shared httpx.AsyncClient in app.state

**What goes wrong:** respx mocks HTTP at the transport level. If the production code uses a single `httpx.AsyncClient` instance stored in `app.state`, that client must be created in a way that respx can intercept. If the client is constructed before `respx.mock` is activated (e.g., at module import time), respx does not intercept its requests. Tests appear to work but actually hit the real Wikimedia API, making them flaky and slow.

**Why it happens:** respx patches the httpx transport. A client created outside the `respx.mock` context (or before the patch is applied) may hold a reference to an unpatched transport.

**Prevention:** Use `respx.mock` as a pytest fixture or decorator that wraps the full test. If using the lifespan-managed client, create it inside the lifespan using `httpx.AsyncClient()` — respx patches the default transport. Verify that respx intercepted all expected calls using `respx.calls.call_count` assertions. Use `respx.mock(assert_all_called=True)` to catch missed mocks.

**Warning signs:** Tests pass when run in isolation but fail intermittently. No `assert_all_called` on respx mocks. Test suite does not stub all Wikimedia endpoints (search, imageinfo, CDN download are three separate hosts).

---

### pytest-asyncio Event Loop Scope Misconfiguration — Module/Session Fixtures Not Sharing Loop

**What goes wrong:** pytest-asyncio 0.21+ deprecated custom `event_loop` fixture overrides and introduced `asyncio_default_fixture_loop_scope`. Without explicit configuration, tests that share a `module`-scoped testcontainers PostgreSQL fixture and `function`-scoped async test functions get a `ScopeMismatch` error or silently create multiple event loops, causing `asyncpg` connections opened in the module-scoped fixture to appear closed in the function-scoped tests.

**Why it happens:** Each pytest-asyncio async fixture runs on an event loop tied to its scope. Async resources opened on a session/module event loop are not usable from a function-scoped event loop. The error surface is confusing — it often manifests as `InterfaceError: connection is closed` rather than an explicit scope error.

**Prevention:** In `pyproject.toml`, set `asyncio_mode = "auto"` and `asyncio_default_fixture_loop_scope = "session"` (or `module` depending on fixture scope). Use a single `module`-scoped `postgres_container` fixture. Keep all database test fixtures at `module` scope to share the container and event loop. Do not mix `scope="function"` async fixtures with `scope="module"` async fixtures without explicitly configuring the loop scope.

**Warning signs:** `ScopeMismatch` error in test output. `InterfaceError: connection is closed` on the first DB operation inside a test. `DeprecationWarning: The event_loop fixture provided by pytest-asyncio has been redefined`.

---

### testcontainers-python Async Driver Failure — Not in Async Context During Container Startup

**What goes wrong:** `testcontainers-python` automatically tries to connect to the database to verify it is ready. When using an async driver (asyncpg via `postgresql+asyncpg://`), this readiness check fails with `sqlalchemy.exc.InvalidRequestError` because the check runs outside an async context.

**Why it happens:** testcontainers' `get_connection_url()` and wait strategies call the driver synchronously. asyncpg only operates inside an async event loop.

**Prevention:** Use `postgresql://` (psycopg2 or psycopg) for the testcontainers connection URL in the wait strategy, and use `postgresql+asyncpg://` only in the actual application engine created inside the test fixture. Or use the `DockerContainer` directly with a TCP wait strategy (`wait_for_logs("database system is ready")`) rather than relying on testcontainers' DB-level ready check. Confirm by checking the open issue: testcontainers/testcontainers-python#263.

**Warning signs:** Tests fail at container startup with `InvalidRequestError` or `greenlet_spawn`. testcontainers container never reports ready. Using `asyncpg` URL in the `PostgresContainer` constructor directly.

---

### FileResponse and Non-Existent File — Unhandled 500 Instead of 404

**What goes wrong:** `FastAPI.FileResponse(path)` raises `FileNotFoundError` if the file does not exist, which FastAPI catches and converts to a 500 by default. If the DB has a row for a vehicle but the file was deleted from disk (e.g., volume was recreated), the service returns 500 instead of falling back to a Wikimedia re-fetch or returning a clean 404.

**Why it happens:** FileResponse does not check file existence before returning — it raises at streaming time. The cache-aside logic reads from DB first, finds a hit, and goes straight to FileResponse without verifying the file exists on disk.

**Prevention:** Before constructing `FileResponse`, assert `path.exists()`. If the file is missing despite a DB row, either (a) re-trigger the Wikimedia fetch and re-cache (self-healing), or (b) delete the stale DB row and return 404. Option (a) is preferred for the "never return 500" contract. A simple `if not path.exists(): raise HTTPException(404)` is the minimum acceptable guard.

**Warning signs:** `FileResponse` called without a preceding `path.exists()` check. No test case for the "DB hit, file missing" scenario. The health check does not verify the volume is writable.

---

### Wikimedia API User-Agent Requirement — Requests Blocked Without Proper Header

**What goes wrong:** Wikimedia's API policy requires a descriptive `User-Agent` header identifying the application and a contact email. Requests without a proper User-Agent are more likely to be rate-limited or blocked. The default httpx User-Agent is `python-httpx/0.x.x`, which is generic and may trigger automated throttling on the Wikimedia side.

**Why it happens:** This is a Wikimedia API policy requirement documented in the API:Etiquette page. It is not enforced with an immediate block, but non-compliant requests are deprioritized and may be blocked during traffic spikes.

**Consequence:** Intermittent Wikimedia API failures that appear random, particularly under load or during Wikimedia infrastructure events.

**Prevention:** Set a descriptive User-Agent on the shared `httpx.AsyncClient` at construction time: `headers={"User-Agent": "carpix-images/1.0 (https://github.com/yourorg/carpix; yourname@example.com)"}`. This is a one-line fix with significant reliability benefit.

**Warning signs:** Default httpx User-Agent in outgoing requests. No User-Agent configuration in the httpx client setup. Intermittent 429 or 503 responses from Wikimedia API.

**Phase:** Phase 1 (httpx client setup) — configure at client construction in lifespan.

---

## Phase-Specific Warning Summary

| Phase Topic | Pitfall | Mitigation |
|---|---|---|
| Wikimedia integration | CDN URL requires MD5 hash subdirs | Always use `thumburl` from imageinfo API, never construct CDN URL manually |
| Wikimedia integration | SVG files produce PNG thumbnails | Filter by `mime: image/jpeg` before selecting a result |
| Wikimedia integration | Empty search results crash on index access | Check `len()` before any list index; use fallback query chain |
| Wikimedia integration | Generic User-Agent triggers throttling | Set descriptive User-Agent on shared AsyncClient |
| Database layer | Using sync SQLAlchemy in async context | Use `create_async_engine`, `AsyncSession`, `mapped_column` from day one |
| Database layer | mypy plugin broken on mypy 1.11+ | Use SQLAlchemy 2.0 native `Mapped[T]` typing; no plugin |
| Core endpoint | Path traversal via URL params | Normalize input, then verify `resolved_path.is_relative_to(BASE_DIR)` |
| Core endpoint | FileResponse 500 on missing file | Check `path.exists()` before FileResponse; handle stale DB rows |
| Cache logic | Race condition on concurrent cache-miss | Per-key asyncio lock or atomic write + ON CONFLICT DO NOTHING |
| HTTP client | Per-request AsyncClient creation | Single client in lifespan, stored on `app.state` |
| Docker/deployment | Volume permissions deny writes | Named volume + Dockerfile chown, or entrypoint.sh with gosu |
| Testing | respx not intercepting lifespan client | Verify respx intercepts all three Wikimedia endpoints; assert_all_called |
| Testing | pytest-asyncio scope mismatch | Set `asyncio_default_fixture_loop_scope = "session"` in pyproject.toml |
| Testing | testcontainers + asyncpg ready check failure | Use psycopg URL in container constructor; asyncpg URL only in app engine |
| Testing | "DB hit, file missing" not covered | Add explicit test case for stale DB row scenario |

---

## Sources

- MediaWiki API:Imageinfo — https://www.mediawiki.org/wiki/API:Imageinfo
- Wikimedia Commons FAQ (MD5 hash subdirectory pattern) — https://commons.wikimedia.org/wiki/Commons:FAQ
- Wikimedia phabricator T109125 (thumburl width guarantee removed) — https://phabricator.wikimedia.org/T109125
- Wikimedia Help:SVG (PNG thumbnail conversion) — https://commons.wikimedia.org/wiki/Help:SVG
- FastAPI lifespan / httpx AsyncClient lifecycle (Medium) — https://medium.com/@benshearlaw/how-to-use-httpx-request-client-with-fastapi-16255a9984a4
- FastAPI lifespan handler example — https://github.com/trondhindenes/fastapi-lifespan-handler
- SQLAlchemy MissingGreenlet error (blog.greeden.me) — https://blog.greeden.me/en/2025/01/29/fastapi-causes-and-solutions-for-sqlalchemy-exc-missinggreenlet-error/
- SQLAlchemy mypy plugin deprecation (SQLAlchemy 2.0 docs) — https://docs.sqlalchemy.org/en/20/orm/extensions/mypy.html
- asyncpg prepared statement cache / pgbouncer — https://github.com/sqlalchemy/sqlalchemy/issues/6467
- testcontainers + async driver issue — https://github.com/testcontainers/testcontainers-python/issues/263
- pytest-asyncio event loop scope deprecation — https://github.com/pytest-dev/pytest-asyncio/issues/924
- respx mocking guide — https://lundberg.github.io/respx/versions/0.14.0/mocking/
- Docker volume permissions (Baeldung) — https://www.baeldung.com/ops/docker-volume-mount-issues
- Atomic file write pattern — https://python-atomicwrites.readthedocs.io/
- FastAPI FileResponse path traversal (CodeSignal) — https://codesignal.com/learn/courses/secure-data-handling-and-integrity-in-fastapi/lessons/secure-file-operations-1
