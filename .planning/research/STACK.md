# Stack Research: Vehicle Image Cache Microservice

**Project:** carpix-images
**Researched:** 2026-05-22
**Domain:** Standalone async FastAPI microservice — HTTP fetch, filesystem cache, PostgreSQL tracking

---

## Recommended Stack

### Core

**fastapi 0.136.1** — The mandatory framework per project constraints. Current stable release
(jumped from 0.115 to 0.136 in the 0.x series — still pre-1.0 API but production-stable). Use
`fastapi[standard]` install extra which pulls in uvicorn, python-multipart, and email-validator
automatically. No alternative considered. — Confidence: High

**uvicorn[standard] 0.47.0** — ASGI server. The `[standard]` extra adds uvloop (faster event
loop on Linux) and httptools (faster HTTP parsing). Single-worker is correct for this service;
Gunicorn multi-worker is only needed when scaling horizontally and adds complexity without
benefit in a sibling-container setup. — Confidence: High

**pydantic-settings 2.14.1** — Typed config via `BaseSettings`. Reads `DATABASE_URL`,
`IMAGES_DIR`, etc. from environment variables automatically. Ships separately from pydantic since
v2. Zero boilerplate for Docker env-var injection. — Confidence: High (official pydantic docs)

**aiofiles 25.1.0** — Required by Starlette's `FileResponse` to stream files without blocking
the event loop. Starlette's older versions used aiofiles directly; newer versions use anyio
internally but the package is still expected in the install. Install it explicitly — omitting it
causes a runtime import error in some Starlette versions. Negligible overhead. — Confidence: High
(confirmed via FastAPI issue #3058 and starlette internals)

---

### Database

**sqlalchemy 2.0.49 + asyncpg 0.31.0** — Use SQLAlchemy 2.0 Core (not ORM) with the
`postgresql+asyncpg` dialect. This project has a single table with four columns and trivial
queries (SELECT by composite PK, INSERT). SQLAlchemy Core gives you parameterised, injection-safe
SQL with type-checked column expressions while avoiding ORM overhead (session management,
identity map, lazy loading) that adds complexity for no benefit at this scale.

asyncpg is the driver choice over psycopg3 because:
- asyncpg is a pure-async driver with no thread-pool adapter layer; it does not block the event
  loop under any condition
- SQLAlchemy 2.0 has first-class asyncpg support via `create_async_engine("postgresql+asyncpg://...")`
- For a cache microservice the bottleneck is the Wikimedia HTTP fetch, not the DB; asyncpg's
  ~15% throughput advantage over psycopg3 is not the deciding factor, but there is no downside
- asyncpg 0.31.0 is the current stable release; well-maintained, widely deployed

Do NOT use the ORM (`AsyncSession`, mapped classes). It adds mapping overhead and lifecycle
complexity (expire-on-commit, session state) that is unnecessary for two-query access patterns. —
Confidence: High (SQLAlchemy official asyncio docs, asyncpg PyPI)

**alembic 1.18.4** — Schema migrations. Run `alembic init -t async` to get an env.py pre-wired
for async engines. The `vehicle_images` table schema is defined once and never changes (no
invalidation, no schema evolution planned), so Alembic is mainly used to create the table on
first deploy and serve as the schema source-of-truth. The async cookbook pattern in Alembic docs
(using `async_engine_from_config` + `run_sync`) is well-established. — Confidence: High
(Alembic official docs)

---

### HTTP Client

**httpx 0.28.1** — The correct async HTTP client for a FastAPI service. Use `AsyncClient` as a
module-level lifespan-managed singleton (created in `@asynccontextmanager lifespan`, closed on
shutdown). Do not create a new client per request — connection pool reuse matters. Configure
`timeout=httpx.Timeout(10.0, connect=5.0)` globally; Wikimedia responses are fast but the
connect step can stall on cold DNS.

httpx is the standard choice here because:
- Native async/await; no thread-pool wrapper unlike requests
- Used by FastAPI's own `TestClient` internally, so the testing integration is seamless
- Wikimedia requires a User-Agent header on API calls; httpx's default headers are clean to
  override at client construction time (`headers={"User-Agent": "carpix-images/1.0 ..."}`)
— Confidence: High (httpx official docs, encode/httpx GitHub)

---

### Testing

**pytest 8.x (via pytest-asyncio 1.3.0 dependency)** — Standard test runner. pytest-asyncio
1.3.0 (the current stable release that jumped from 0.26 to 1.x) is the async test harness. Set
`asyncio_mode = "auto"` in `pyproject.toml` to avoid decorating every test with
`@pytest.mark.asyncio`. — Confidence: High

**pytest-asyncio 1.3.0** — Use `asyncio_mode = "auto"` and `asyncio_default_fixture_loop_scope =
"session"` in pyproject.toml. The 1.x release stabilised the loop-scope API that was in flux
through 0.21-0.26. Important: use `@pytest_asyncio.fixture` (not `@pytest.fixture`) for async
fixtures to avoid the deprecation warning introduced in 0.21. — Confidence: High (pytest-asyncio
official docs)

**respx 0.23.1** — Mock all outbound Wikimedia HTTP calls. Use `@respx.mock` decorator or
`async with respx.mock` context manager on tests that exercise the fetch path. respx intercepts
at the httpx transport layer, so no global monkey-patching occurs and the mock is scoped to the
test. This is the correct choice over `pytest-httpx` for this project because:
- respx integrates directly with httpx transport (no patching, no leakage between tests)
- URL pattern matching (`respx.get("https://commons.wikimedia.org/...").respond(...)`) is
  expressive and catches misconfigured URLs at test time
- async-native by design, not an afterthought
— Confidence: High (respx GitHub, multiple 2025 FastAPI community sources)

**testcontainers 4.14.2** — Spin up a real PostgreSQL container for integration tests.
Use `testcontainers[postgres]` extra. Create a session-scoped fixture that starts
`PostgresContainer("postgres:16")` once, runs Alembic migrations against it, and yields the
connection URL. Individual tests use function-scoped async engine/connection fixtures derived from
it. This gives real SQL behaviour (constraint violations, transaction rollback) without a
persistent local Postgres. — Confidence: High (testcontainers official docs, 2025 FastAPI
integration examples)

**httpx AsyncClient as TestClient** — For endpoint tests (not just unit tests), use
`httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test")`. This exercises the
full ASGI stack without a real server. Pair with respx mocks for the Wikimedia calls and the
testcontainers Postgres for DB assertions. — Confidence: High (FastAPI official testing docs)

---

### Tooling

**ruff 0.15.14** — Linter and formatter in one binary. Replaces black, flake8, isort, pyupgrade.
In pyproject.toml configure:
```toml
[tool.ruff]
line-length = 88
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM"]
ignore = ["E501"]

[tool.ruff.format]
quote-style = "double"
```
The `B` (bugbear) and `SIM` (simplify) rule sets catch async-specific mistakes (e.g., `B007`
unused loop variable, `B023` function in loop) that matter in this codebase. — Confidence: High
(ruff official docs, astral-sh/ruff GitHub)

**mypy 2.1.0** — Use `strict = true` in pyproject.toml. FastAPI is fully typed; SQLAlchemy 2.0
ships with inline types; httpx ships with inline types; asyncpg ships stubs. The only friction
point is testcontainers — its type stubs are partial. Suppress with `# type: ignore[...]` at the
fixture boundary rather than weakening the global config. — Confidence: High

**uv** (latest, no pinned version — it's a system tool) — Package manager replacing pip + venv.
Use `uv sync` for reproducible installs, `uv run` to execute commands in the project venv. The
Dockerfile copies `uv` from `ghcr.io/astral-sh/uv` and runs `uv sync --frozen --no-cache` for
deterministic container builds. — Confidence: High (astral-sh/uv official docs, 2025 FastAPI
Docker guides)

---

## What NOT to Use

**psycopg3 (psycopg[binary])** — Asyncpg is the better async PostgreSQL driver for this use
case. psycopg3 has a sync-to-async adapter layer for its DBAPI2 surface; asyncpg was written
async-first. The psycopg3 "Row Factories" feature (mapping rows to Pydantic models) is
compelling for read-heavy ORM-adjacent patterns, but this project uses two trivial queries and
already has Pydantic for request/response schemas, so the feature provides no net benefit.
Switch to psycopg3 only if asyncpg causes unexplained connection pool exhaustion or ENUM
handling issues (known asyncpg JIT bug — mitigated with `server_settings={"jit": "off"}`).

**SQLAlchemy ORM / AsyncSession** — Mapped classes and session lifecycle management add
complexity without benefit for a two-query service. The ORM's `expire_on_commit` default silently
issues extra SELECT statements after inserts unless disabled explicitly — this is a footgun in
async code. Use Core `Table` + `insert()`/`select()` directly.

**encode/databases** — Older async DB layer that predates SQLAlchemy 2.0's native async support.
FastAPI's own docs still reference it in legacy examples. Superseded. Do not use.

**aiohttp** — An async HTTP client/server framework. Viable as an HTTP client but httpx is the
idiomatic choice for FastAPI projects and is already in the dependency graph (FastAPI's TestClient
is built on httpx). Using aiohttp introduces a second async HTTP abstraction with no benefit.

**Pillow / PIL** — Explicitly out of scope. Wikimedia CDN handles the 800px thumbnail
server-side via the `/thumb/` URL pattern. No local image processing needed.

**Redis** — Not needed. The cache semantics are "permanent once written"; filesystem + PostgreSQL
is sufficient and matches the project constraint of zero additional infrastructure.

**Celery / ARQ / background task queues** — The Wikimedia fetch is fast enough to execute
synchronously within the request lifecycle (httpx async, ~1-2s). Background workers introduce
deployment complexity (worker process, broker) for a latency budget that doesn't require it.
FastAPI's `BackgroundTasks` is also unnecessary — the caller expects the image in the response
body, not a deferred job.

**pytest-httpx** — Weaker alternative to respx. pytest-httpx patches httpx globally and is
harder to scope. respx's transport-layer interception model is cleaner and better matches the
project's lifespan-managed `AsyncClient` singleton pattern.

---

## Key Trade-offs

**SQLAlchemy Core vs raw asyncpg queries**

Raw asyncpg (`conn.fetch("SELECT ...", ...)`) is 5-10% faster and has zero abstraction overhead.
SQLAlchemy Core adds ~0.5ms per query in exchange for: parameterised query objects that are
statically type-checkable, schema-as-code (`Table()` definition), and Alembic integration (Alembic
reads the `MetaData` object to autogenerate migrations). For a service with two query types and a
requirement for `ruff + mypy clean`, the type safety and migration story of SQLAlchemy Core win.
If performance becomes a concern (unlikely — the bottleneck is always the Wikimedia HTTP call),
drop to raw asyncpg only on the hot path.

**Testcontainers vs docker-compose for integration tests**

docker-compose requires the developer to manually start services before running tests; testcontainers
spins up a Postgres container automatically inside the pytest session and tears it down afterwards.
For a TDD workflow this is strictly better — `pytest` is a complete, self-contained command.
The tradeoff: testcontainers requires Docker to be running on the test machine (true in any
CI environment and on developer machines for this Docker-deployed project). Container startup adds
~3-5s to the first test run in a session; subsequent tests in the same session reuse the container.

**asyncio_mode = "auto" vs explicit @pytest.mark.asyncio**

`asyncio_mode = "auto"` in pyproject.toml marks all async test functions as asyncio tests
automatically. This eliminates boilerplate and prevents the silent failure mode where a test is
`async def` but lacks the marker — pytest runs it synchronously and it passes vacuously (never
actually awaiting anything). The only downside is it changes the default for the entire test
suite; acceptable for a service that is async throughout.

**FileResponse vs StreamingResponse for images**

`FileResponse` is the correct choice. It sets `Content-Length`, `Last-Modified`, and `ETag`
headers automatically from the filesystem, enabling HTTP caching by the caller (carpix parent
service). `StreamingResponse` with manual file reading provides no additional benefit and
requires aiofiles boilerplate. Both require aiofiles installed.

---

## Installation

```toml
# pyproject.toml
[project]
name = "carpix-images"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi[standard]>=0.136.1",
    "uvicorn[standard]>=0.47.0",
    "sqlalchemy>=2.0.49",
    "asyncpg>=0.31.0",
    "alembic>=1.18.4",
    "httpx>=0.28.1",
    "pydantic-settings>=2.14.1",
    "aiofiles>=25.1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=1.3.0",
    "respx>=0.23.1",
    "testcontainers[postgres]>=4.14.2",
    "ruff>=0.15.14",
    "mypy>=2.1.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "session"

[tool.ruff]
line-length = 88
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM"]

[tool.mypy]
strict = true
python_version = "3.12"
```

---

## Sources

- FastAPI official docs: https://fastapi.tiangolo.com/advanced/custom-response/ (FileResponse)
- SQLAlchemy asyncio docs: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
- asyncpg PyPI: https://pypi.org/project/asyncpg/
- Alembic async cookbook: https://alembic.sqlalchemy.org/en/latest/cookbook.html
- httpx official docs: https://www.python-httpx.org/advanced/timeouts/
- respx GitHub: https://github.com/lundberg/respx
- pytest-asyncio docs: https://pytest-asyncio.readthedocs.io/
- testcontainers-python docs: https://testcontainers-python.readthedocs.io/
- testcontainers + FastAPI + asyncpg: https://lealre.github.io/fastapi-testcontainer-asyncpg/
- ruff configuration: https://docs.astral.sh/ruff/configuration/
- uv + FastAPI + Docker: https://docs.astral.sh/uv/guides/integration/fastapi/
- asyncpg vs psycopg3 comparison: https://fernandoarteaga.dev/blog/psycopg-vs-asyncpg/
- Modern Python tooling 2026: https://softaims.com/blog/modern-python-tooling-uv-ruff-mypy-2026
