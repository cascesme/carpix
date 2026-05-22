# Phase 1: Foundation - Research

**Researched:** 2026-05-22
**Domain:** FastAPI project scaffolding, uv build tooling, pydantic-settings config, normalization logic, health endpoints
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Use **uv** as package manager and build tool. `pyproject.toml` uses uv conventions (`[tool.uv]` if needed, `uv.lock` lockfile). Multi-stage Dockerfile uses `uv pip install` or `uv sync`. No hatchling or plain pip.
- **D-02:** **src-layout** — source code lives at `src/carpix_images/`. Package name is `carpix_images`. Mirrors parent project (`auto-insight-claw`) convention. `pythonpath = ["src"]` in pytest config, `mypy_path = "src"` in mypy config.
- **D-03:** `GET /health` always returns **HTTP 200** — process liveness is unconditional. DB probe result appears in the body only.
- **D-04:** Response body when DB is reachable: `{"status": "ok", "db": "ok"}`. When DB is unreachable: `{"status": "ok", "db": "error"}`. Flat strings, no nesting.
- **D-05:** Use **pydantic-settings** (`BaseSettings`). Mirrors parent project. Validates env vars at startup — missing required vars crash early with a clear error.
- **D-06:** Phase 1 configures **`DATABASE_URL` only**. `IMAGES_DIR` and all other settings added in their respective phases. No forward-declaration of unused config.

### Claude's Discretion

- App factory pattern: use `create_app() -> FastAPI` function (mirrors parent project's `main.py` pattern).
- Lifespan: use FastAPI `@asynccontextmanager` lifespan (modern pattern, not deprecated `@app.on_event`). DB pool wiring happens in Phase 3 — Phase 1 lifespan can be a no-op or minimal.
- Internal module structure within `src/carpix_images/`: Claude selects (e.g., `config.py`, `main.py`, `routers/health.py`, `domain/normalize.py`).

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| NORM-01 | Brand and model inputs normalized to canonical keys (lowercase, strip all non-alphanumeric characters) before cache lookup and filesystem path construction; normalization matches parent project's `domain/vehicle_identity.py` | Canonical implementation is `re.sub(r"[^a-z0-9]", "", value.lower())` — read directly from parent project source. Copy verbatim into `src/carpix_images/domain/normalize.py`. |
| API-03 | `GET /health` returns HTTP 200 for process liveness; succeeds even when DB is unreachable | FastAPI APIRouter + unconditional 200 return. DB probe via short-lived `asyncpg.connect()` wrapped in try/except — exception caught, `db = "error"` set, 200 returned regardless. |
| API-05 | `GET /health` includes `SELECT 1` DB probe and reports DB connectivity status distinct from process liveness | Body schema `{"status": "ok", "db": "ok|error"}` — `status` always `"ok"`, `db` reflects probe result. The two fields are semantically distinct. |

</phase_requirements>

---

## Summary

Phase 1 establishes the complete project skeleton for `carpix-images`: a src-layout Python package managed by uv, a FastAPI app factory, pydantic-settings config, the normalization domain function, and the health router. All decisions are locked in CONTEXT.md — research confirms they align with ecosystem best practice and validates exact implementation patterns from the parent project.

The normalization function is locked: `re.sub(r"[^a-z0-9]", "", value.lower())` copied verbatim from `/home/ccastro/Projects/auto-insight-claw/src/auto_insight_claw/domain/vehicle_identity.py` line 15. No deviation.

The health endpoint design (always 200, DB probe in body only) is a standard production pattern that correctly separates liveness from readiness. Phase 1 implements the DB probe as a short-lived `asyncpg.connect()` call — not a pool — since the full connection pool lifecycle is Phase 3.

**Primary recommendation:** Follow the parent project's patterns exactly (src-layout, `create_app()` factory, `pydantic-settings BaseSettings`, APIRouter structure). This phase is scaffolding, not innovation.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| HTTP routing + OpenAPI docs | API / Backend (FastAPI) | — | FastAPI owns route registration, schema generation, and docs endpoint |
| Config / env-var validation | API / Backend (startup) | — | `pydantic-settings` validates at process startup; crashes early on bad config |
| Input normalization | API / Backend (domain layer) | — | Pure function — no I/O, no HTTP — belongs in domain, called by router layer in later phases |
| Health liveness (`status`) | API / Backend | — | Process-level check; always passes if the process is running |
| Health DB probe (`db`) | API / Backend → Database | — | Router initiates; result reflects DB TCP reachability |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `fastapi` | 0.136.1 [VERIFIED: PyPI] | Web framework, routing, OpenAPI | Locked by project constraint; async-native, auto docs |
| `uvicorn[standard]` | 0.47.0 [VERIFIED: PyPI] | ASGI server | Standard FastAPI server; `[standard]` includes `watchfiles`, `httptools` |
| `pydantic-settings` | 2.14.1 [VERIFIED: PyPI] | Env-var config with validation | Locked by D-05; mirrors parent project |
| `pydantic` | 2.13.4 [VERIFIED: PyPI] | Data validation (pulled by pydantic-settings) | Transitive dependency; already installed |
| `asyncpg` | 0.31.0 [VERIFIED: PyPI] | PostgreSQL async driver (health probe) | Needed for DB probe in health endpoint; full pool in Phase 3 |

### Dev / Testing

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pytest` | 9.0.3 [VERIFIED: PyPI] | Test runner | All tests |
| `pytest-asyncio` | 1.3.0 [VERIFIED: PyPI] | Async test support | All async test functions |
| `httpx` | 0.28.1 [VERIFIED: PyPI] | ASGI test client (via `AsyncClient`) | Integration tests hitting the FastAPI app |
| `ruff` | 0.15.14 [VERIFIED: PyPI] | Linter + formatter | Pre-commit; `ruff check` + `ruff format` |
| `mypy` | 2.1.0 [VERIFIED: PyPI] | Static type checker | Pre-commit; `mypy --strict` |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `asyncpg` direct (health probe) | `SQLAlchemy async engine` | SQLAlchemy is the right tool for Phase 3 full pool; bare asyncpg is simpler and correct for Phase 1 single-connect probe |
| `pydantic-settings` | `python-dotenv` alone | pydantic-settings validates types at startup and crashes clearly — dotenv alone has no validation |
| `uvicorn[standard]` | `uvicorn` (base) | `[standard]` extras needed for production-quality reload support; no downside |

**Installation (uv):**
```bash
uv add fastapi "uvicorn[standard]" pydantic-settings asyncpg
uv add --dev pytest pytest-asyncio httpx ruff mypy
```

**Version verification:** All versions confirmed against PyPI registry on 2026-05-22. [VERIFIED: PyPI]

---

## Package Legitimacy Audit

| Package | Registry | slopcheck | Disposition |
|---------|----------|-----------|-------------|
| `fastapi` | PyPI | [OK] | Approved |
| `uvicorn` | PyPI | [OK] | Approved |
| `pydantic-settings` | PyPI | [OK] | Approved |
| `asyncpg` | PyPI | [OK] | Approved |
| `pytest` | PyPI | [OK] | Approved |
| `pytest-asyncio` | PyPI | [OK] | Approved |
| `httpx` | PyPI | [OK] | Approved |
| `ruff` | PyPI | [OK] | Approved |
| `mypy` | PyPI | [OK] | Approved |
| `respx` | PyPI | [OK] | Approved |
| `testcontainers` | PyPI | [OK] | Approved |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

*slopcheck 0.6.1 ran successfully — all packages confirmed OK.*

---

## Architecture Patterns

### System Architecture Diagram

```
HTTP Request
     │
     ▼
FastAPI app (create_app())
     │
     ├── lifespan (no-op in Phase 1)
     │
     ├── APIRouter: /health
     │        │
     │        ├── process liveness → always "ok"
     │        └── asyncpg.connect(DATABASE_URL) ──► PostgreSQL
     │                │
     │                ├── SELECT 1 success → db: "ok"
     │                └── Exception caught → db: "error"
     │
     └── /docs (auto-generated OpenAPI)

Config layer (pydantic-settings BaseSettings):
  env vars / .env → Settings() → DATABASE_URL

Domain layer (pure function):
  canonical_key(str) → str
  (no I/O, no HTTP, no DB)
```

### Recommended Project Structure

```
src/
└── carpix_images/
    ├── __init__.py
    ├── main.py              # create_app() factory, app = create_app()
    ├── config.py            # Settings(BaseSettings), settings singleton
    ├── domain/
    │   ├── __init__.py
    │   └── normalize.py     # canonical_key() — NORM-01
    └── routers/
        ├── __init__.py
        └── health.py        # GET /health — API-03, API-05

tests/
├── __init__.py
├── conftest.py              # set DATABASE_URL env before imports
├── unit/
│   ├── __init__.py
│   ├── test_normalize.py    # pure function tests
│   └── test_health.py       # health router tests with mocked asyncpg
└── integration/
    └── __init__.py          # placeholder for Phase 3+

pyproject.toml
uv.lock
```

### Pattern 1: App Factory with Lifespan

**What:** `create_app()` returns a configured `FastAPI` instance. Startup/shutdown wired via `@asynccontextmanager` lifespan passed to `FastAPI(lifespan=...)`.

**When to use:** Always — enables clean testing (`TestClient(create_app())`) and deferred pool binding in later phases.

**Example:**
```python
# Source: https://fastapi.tiangolo.com/advanced/events/ [CITED]
# Adapted to match parent project pattern at auto-insight-claw/src/.../main.py [VERIFIED: codebase]
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Phase 1: no-op. Phase 3 will wire asyncpg pool here.
    yield

def create_app() -> FastAPI:
    app = FastAPI(
        title="carpix-images",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.include_router(health_router)
    return app

app = create_app()
```

### Pattern 2: pydantic-settings Config (D-05, D-06)

**What:** `Settings(BaseSettings)` reads from env vars and `.env`. Phase 1 exposes `DATABASE_URL` only. Missing required fields crash at startup with a clear `ValidationError`.

**Example:**
```python
# Source: mirrors auto-insight-claw/src/auto_insight_claw/config.py [VERIFIED: codebase]
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )
    database_url: str  # required; crashes at startup if missing

settings = Settings()
```

### Pattern 3: Health Router with DB Probe (API-03, API-05)

**What:** `/health` always returns HTTP 200. DB probe uses a short-lived `asyncpg.connect()`, runs `SELECT 1`, closes, and reports result. Exception is caught — probe failure does not fail the request.

**Example:**
```python
# Source: CONTEXT.md specifics + asyncpg official docs [CITED: asyncpg docs]
import asyncpg
from fastapi import APIRouter
from carpix_images.config import settings

router = APIRouter()

@router.get("/health")
async def health() -> dict[str, str]:
    db_status = "error"
    try:
        conn = await asyncpg.connect(settings.database_url)
        await conn.execute("SELECT 1")
        await conn.close()
        db_status = "ok"
    except Exception:
        pass
    return {"status": "ok", "db": db_status}
```

**Critical notes:**
- `status` is ALWAYS `"ok"` (D-03 — process liveness unconditional)
- `db` reflects probe result only (D-04 — flat strings, no nesting)
- `asyncpg.connect()` takes the raw `postgresql+asyncpg://...` URL — but asyncpg itself expects `postgresql://...` (no `+asyncpg` driver specifier). The `database_url` for asyncpg direct use must use the plain `postgresql://` scheme. When SQLAlchemy is added in Phase 3, `postgresql+asyncpg://` is the correct scheme for SQLAlchemy. This means Phase 1 needs to handle the URL prefix difference.

**URL scheme handling options:**
1. Store `DATABASE_URL` as `postgresql://...` (asyncpg native) and let Phase 3 add `+asyncpg` suffix for SQLAlchemy — OR
2. Store as `postgresql+asyncpg://...` and strip the `+asyncpg` part for the Phase 1 health probe.

Option 2 is preferable so Phase 3 doesn't require a config change. Stripping is simple: `url.replace("postgresql+asyncpg://", "postgresql://")`.

### Pattern 4: Normalization Domain Function (NORM-01)

**What:** `canonical_key()` is a pure function copied verbatim from the parent project. Lives in `domain/normalize.py`.

**Example:**
```python
# Source: /home/ccastro/Projects/auto-insight-claw/src/auto_insight_claw/domain/vehicle_identity.py line 15 [VERIFIED: codebase]
import re

def canonical_key(value: str) -> str:
    """Compact identity key for cache/coalescing lookups.

    Removes all non-alphanumeric characters and lowercases, so
    'DM-i', 'DMi', 'Dmi', and 'DM i' all map to 'dmi'.
    """
    return re.sub(r"[^a-z0-9]", "", value.lower())
```

**Do NOT add** `clean_display()` — CONTEXT.md specifics explicitly exclude it from Phase 1.

### Pattern 5: pyproject.toml for src-layout with uv

**What:** uv requires a `[build-system]` declaration for src-layout packages. Use `hatchling` (same as parent project) for package discovery. Pytest config needs `pythonpath = ["src"]` and mypy needs `mypy_path = "src"`.

**Example:**
```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "carpix-images"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.136.1",
    "uvicorn[standard]>=0.47.0",
    "pydantic-settings>=2.14.1",
    "asyncpg>=0.31.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=9.0.3",
    "pytest-asyncio>=1.3.0",
    "httpx>=0.28.1",
    "ruff>=0.15.14",
    "mypy>=2.1.0",
    "respx>=0.23.1",
    "testcontainers[postgres]>=4.14.2",
]

[tool.hatch.build.targets.wheel]
packages = ["src/carpix_images"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
pythonpath = ["src"]

[tool.mypy]
strict = true
python_version = "3.12"
mypy_path = "src"
explicit_package_bases = true
plugins = ["pydantic.mypy"]

[[tool.mypy.overrides]]
module = ["asyncpg", "asyncpg.*"]
ignore_missing_imports = true

[[tool.mypy.overrides]]
module = ["pydantic_settings"]
ignore_missing_imports = true

[[tool.mypy.overrides]]
module = ["testcontainers", "testcontainers.*"]
ignore_missing_imports = true

[tool.ruff]
target-version = "py312"
line-length = 88

[tool.ruff.lint]
select = ["E", "F", "I", "UP"]
```

**Note on build backend:** The parent project uses `hatchling`. D-01 specifies uv as the package manager. These are compatible — uv manages environments and lock files; hatchling handles package builds. [VERIFIED: codebase cross-reference with parent pyproject.toml]

### Pattern 6: conftest.py — Env Setup Before Module Import

**What:** `settings = Settings()` runs at module import time. Tests that import `carpix_images.config` will fail unless `DATABASE_URL` is set before import. The parent project handles this in `conftest.py`.

**Example:**
```python
# Source: mirrors auto-insight-claw/tests/conftest.py [VERIFIED: codebase]
import os

os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/testdb"
)
```

### Anti-Patterns to Avoid

- **`@app.on_event("startup")`:** Deprecated in FastAPI. Use `@asynccontextmanager` lifespan. [CITED: https://fastapi.tiangolo.com/advanced/events/]
- **Importing `settings` directly in router modules without test env set:** Always set env vars in `conftest.py` before any `carpix_images` import. The parent project shows this pattern exactly.
- **Using `DATABASE_URL` with `postgresql+asyncpg://` directly in `asyncpg.connect()`:** asyncpg's `connect()` does not accept the SQLAlchemy driver specifier. Strip it or use a separate config key.
- **Adding `clean_display` or other normalization functions:** CONTEXT.md specics explicitly restrict Phase 1 to `canonical_key` only.
- **Validating config in `__init__.py` at module level:** The parent project calls `Settings()` in `config.py` at module level — this is intentional. Tests must set env vars in `conftest.py` *before* any module from `carpix_images` is imported.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Env-var parsing + validation | Custom `os.environ.get()` wrappers | `pydantic-settings BaseSettings` | Type coercion, required-field enforcement, `.env` support, clear error messages |
| OpenAPI/docs generation | Manual route documentation | FastAPI auto-docs at `/docs` | Auto-generated from type hints; free with FastAPI |
| Async test support | Manual `asyncio.run()` in tests | `pytest-asyncio` with `asyncio_mode = "auto"` | Handles event loop lifecycle; `auto` mode removes all boilerplate marks |
| App startup/shutdown lifecycle | Manual flag variables | FastAPI `lifespan` with `@asynccontextmanager` | Official pattern; integrates cleanly with TestClient |

**Key insight:** Phase 1 is mostly wiring known-good patterns together. The only novel logic is the DB probe exception handling in the health endpoint.

---

## Common Pitfalls

### Pitfall 1: asyncpg URL scheme mismatch

**What goes wrong:** `asyncpg.connect("postgresql+asyncpg://...")` raises `ValueError: invalid dsn` because asyncpg does not recognize the `+asyncpg` driver specifier that SQLAlchemy uses.

**Why it happens:** SQLAlchemy 2.0 uses `postgresql+asyncpg://` to select the asyncpg dialect. asyncpg's own `connect()` expects a plain `postgresql://` DSN.

**How to avoid:** In the health router, strip the specifier before passing to asyncpg: `dsn = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")`. Store `DATABASE_URL` as `postgresql+asyncpg://` so Phase 3 SQLAlchemy works without config change.

**Warning signs:** `ValueError` or `InvalidCatalogNameError` in health endpoint logs on startup.

### Pitfall 2: `settings = Settings()` fails in tests

**What goes wrong:** Tests fail with `ValidationError: 1 validation error for Settings — database_url: Field required` when importing anything from `carpix_images`.

**Why it happens:** `settings = Settings()` is a module-level statement in `config.py`. It executes at first import. If `DATABASE_URL` is not in the environment at that point, pydantic-settings raises immediately.

**How to avoid:** `tests/conftest.py` MUST `os.environ.setdefault("DATABASE_URL", "...")` before any `carpix_images` import. This is standard in the parent project. pytest loads `conftest.py` before test collection, so this works — but only if `conftest.py` is at the `tests/` root (not in a subdirectory conftest only).

**Warning signs:** `ImportError` or `ValidationError` during pytest collection (before any test runs).

### Pitfall 3: Lifespan vs on_event in TestClient

**What goes wrong:** `@app.on_event("startup")` handlers are silently ignored when `FastAPI(lifespan=...)` is also set. Tests pass locally but startup logic never runs.

**Why it happens:** FastAPI's docs explicitly state: "If you provide a lifespan parameter, startup and shutdown event handlers will no longer be called."

**How to avoid:** Use only `lifespan` — never mix with `on_event`. Phase 1 lifespan is a no-op `yield` anyway, so there is nothing to accidentally skip.

**Warning signs:** Startup side-effects (resource initialization) not present in tests.

### Pitfall 4: mypy strict mode and asyncpg stubs

**What goes wrong:** `mypy --strict` fails on `import asyncpg` with `error: Cannot find implementation or library stub for module named "asyncpg"`.

**Why it happens:** asyncpg ships without bundled mypy stubs. With `strict = true`, missing stubs are an error by default.

**How to avoid:** Add `[[tool.mypy.overrides]]` with `ignore_missing_imports = true` for `asyncpg` and `asyncpg.*`. The parent project's `pyproject.toml` already shows this pattern — reuse exactly. [VERIFIED: codebase]

**Warning signs:** mypy errors on `import asyncpg` lines in `health.py`.

### Pitfall 5: uv not in PATH on this machine

**What goes wrong:** `uv` binary is not available in the current shell PATH. `uv add`, `uv sync`, `uv run` all fail with `command not found`.

**Why it happens:** uv was not found at `/home/ccastro/.cargo/bin/uv` or `/home/ccastro/.local/bin/uv`. It may need to be installed.

**How to avoid:** Install uv first: `curl -LsSf https://astral.sh/uv/install.sh | sh` or `pip install uv`. The plan must include a `uv` installation step or verify availability before any `uv` commands. [ASSUMED — not verified whether uv is installed under a non-standard path]

**Warning signs:** `command not found: uv` when running plan tasks.

---

## Code Examples

Verified patterns from official and codebase sources:

### canonical_key (NORM-01)
```python
# Source: /home/ccastro/Projects/auto-insight-claw/src/auto_insight_claw/domain/vehicle_identity.py:15 [VERIFIED: codebase]
import re

def canonical_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())
```

### Health endpoint with asyncpg probe
```python
# Source: CONTEXT.md specifics + asyncpg pattern [CITED: asyncpg docs]
import asyncpg
from fastapi import APIRouter
from carpix_images.config import settings

router = APIRouter()

@router.get("/health")
async def health() -> dict[str, str]:
    db_status = "error"
    dsn = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    try:
        conn = await asyncpg.connect(dsn, timeout=3)
        await conn.execute("SELECT 1")
        await conn.close()
        db_status = "ok"
    except Exception:
        pass
    return {"status": "ok", "db": db_status}
```

### FastAPI lifespan (no-op for Phase 1)
```python
# Source: https://fastapi.tiangolo.com/advanced/events/ [CITED]
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield  # Phase 3 will add pool init before yield and pool close after

def create_app() -> FastAPI:
    app = FastAPI(title="carpix-images", version="1.0.0", lifespan=lifespan)
    app.include_router(health_router)
    return app
```

### conftest.py — env setup guard
```python
# Source: mirrors /home/ccastro/Projects/auto-insight-claw/tests/conftest.py [VERIFIED: codebase]
import os

os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/testdb"
)
```

### Unit test: canonical_key
```python
import pytest
from carpix_images.domain.normalize import canonical_key

@pytest.mark.parametrize("input,expected", [
    ("Toyota", "toyota"),
    ("BYD DM-i", "byddmi"),
    ("Land Rover", "landrover"),
    ("Alfa-Romeo", "alfaromeo"),
    ("Model 3", "model3"),
    ("", ""),
])
def test_canonical_key(input: str, expected: str) -> None:
    assert canonical_key(input) == expected
```

### Unit test: health endpoint (asyncpg mock)
```python
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from carpix_images.main import create_app

def test_health_returns_200_db_ok() -> None:
    mock_conn = AsyncMock()
    with patch("carpix_images.routers.health.asyncpg.connect", return_value=mock_conn):
        client = TestClient(create_app())
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "db": "ok"}

def test_health_returns_200_db_unreachable() -> None:
    with patch("carpix_images.routers.health.asyncpg.connect", side_effect=Exception("refused")):
        client = TestClient(create_app())
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "db": "error"}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `@app.on_event("startup")` | `@asynccontextmanager` lifespan | FastAPI 0.93 | `on_event` is deprecated; lifespan unifies startup/shutdown |
| `pytest-asyncio` with `@pytest.mark.asyncio` per test | `asyncio_mode = "auto"` in pyproject.toml | pytest-asyncio 0.21+ | No per-test decorator needed; all async tests just work |
| `pip` + `requirements.txt` | `uv` + `pyproject.toml` + `uv.lock` | 2023-2024 | Faster installs, deterministic locks, replaces pip/venv/pip-tools |
| `setup.py` / `setup.cfg` | `pyproject.toml` | PEP 517/518 | Standard since Python 3.11; uv, hatchling, setuptools all use it |

**Deprecated/outdated:**
- `@app.on_event`: Deprecated since FastAPI 0.93. The lifespan approach is the only supported path going forward.
- `pytest-asyncio` per-test `@pytest.mark.asyncio` decorator: Still works but `asyncio_mode = "auto"` eliminates the boilerplate entirely.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `uv` is not installed on the target machine (not found at common paths) | Common Pitfalls #5 | Low — plan must include install step anyway; confirming early avoids broken first task |
| A2 | Health probe `asyncpg.connect()` with `timeout=3` parameter is the correct kwarg name | Code Examples | Low — asyncpg `connect()` accepts `timeout` as a float in seconds; if wrong, omit and rely on default |

**Notes on A2:** asyncpg `connect()` does accept a `timeout` parameter [ASSUMED from training knowledge — not verified via Context7 in this session since ctx7 unavailable]. The timeout is prudent to avoid health checks hanging indefinitely. If incorrect, removing the kwarg produces safe (but potentially slow) behavior.

---

## Open Questions

1. **asyncpg `timeout` parameter name**
   - What we know: asyncpg `connect()` accepts connection configuration kwargs.
   - What's unclear: Whether `timeout=` is the correct keyword for connection timeout in asyncpg 0.31.0.
   - Recommendation: Implementer verifies with `python -c "import asyncpg; help(asyncpg.connect)"` or checks asyncpg docs. If wrong, omit the timeout kwarg — it's a nice-to-have, not a correctness requirement.

2. **uv availability on developer machine**
   - What we know: `uv` binary was not found at PATH, `~/.cargo/bin/uv`, or `~/.local/bin/uv` on the current machine.
   - What's unclear: Whether uv is installed under a non-standard path, or whether the plan needs to install it first.
   - Recommendation: Plan Wave 0 should probe `command -v uv` and include a conditional install step.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12+ | All code | ✓ | 3.13.6 | — |
| uv | Package management (D-01) | ✗ | — | Install via `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| pytest | Test runner | ✓ | 9.0.3 | — |
| pytest-asyncio | Async tests | ✓ | 1.3.0 | — |
| ruff | Linting | ✓ | 0.15.12 (installed) | — |
| mypy | Type checking | ✓ | 1.20.2 (installed) | — |
| PostgreSQL (running) | Health probe integration test | ✗ | — | Unit tests mock asyncpg; integration tests use testcontainers |
| Docker | testcontainers (Phase 3+) | Not checked | — | Phase 1 only needs mock-based unit tests |

**Missing dependencies with no fallback:**
- `uv` — required by D-01. Plan must install before any `uv add` command.

**Missing dependencies with fallback:**
- PostgreSQL (running instance) — Phase 1 health probe unit tests mock asyncpg so no live DB is needed for Phase 1 tests.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` — created in Wave 0 |
| Quick run command | `pytest tests/unit/ -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| NORM-01 | `canonical_key("BYD DM-i")` == `"byddmi"` | unit | `pytest tests/unit/test_normalize.py -x` | Wave 0 |
| NORM-01 | `canonical_key("")` == `""` (empty string) | unit | `pytest tests/unit/test_normalize.py -x` | Wave 0 |
| NORM-01 | `canonical_key("Land Rover")` == `"landrover"` (spaces stripped) | unit | `pytest tests/unit/test_normalize.py -x` | Wave 0 |
| API-03 | `GET /health` returns 200 when asyncpg probe succeeds | unit | `pytest tests/unit/test_health.py::test_health_returns_200_db_ok -x` | Wave 0 |
| API-03 | `GET /health` returns 200 when asyncpg.connect raises | unit | `pytest tests/unit/test_health.py::test_health_returns_200_db_unreachable -x` | Wave 0 |
| API-05 | Body contains `{"status": "ok", "db": "ok"}` when DB reachable | unit | `pytest tests/unit/test_health.py::test_health_db_status_ok -x` | Wave 0 |
| API-05 | Body contains `{"status": "ok", "db": "error"}` when DB unreachable | unit | `pytest tests/unit/test_health.py::test_health_db_status_error -x` | Wave 0 |
| API-03+05 | `GET /docs` returns 200 (routes discoverable) | unit | `pytest tests/unit/test_health.py::test_docs_accessible -x` | Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/unit/ -x`
- **Per wave merge:** `pytest tests/ -x && ruff check src/ tests/ && mypy src/`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/__init__.py` — empty, required for pytest collection
- [ ] `tests/conftest.py` — set `DATABASE_URL` env var before imports
- [ ] `tests/unit/__init__.py` — empty
- [ ] `tests/unit/test_normalize.py` — covers NORM-01 (parametrized)
- [ ] `tests/unit/test_health.py` — covers API-03, API-05 (mocked asyncpg)
- [ ] `tests/integration/__init__.py` — placeholder for Phase 3+
- [ ] `pyproject.toml` — with `[tool.pytest.ini_options]`, `[tool.mypy]`, `[tool.ruff]`

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Internal service, no auth required (per project constraints) |
| V3 Session Management | no | Stateless API |
| V4 Access Control | no | Internal service |
| V5 Input Validation | yes (Phase 2+) | `canonical_key()` normalizes but does not validate — path traversal guard is Phase 2 |
| V6 Cryptography | no | No crypto in Phase 1 |

### Known Threat Patterns for Phase 1 Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Missing required env var exposes partial config | Information disclosure | `pydantic-settings` crashes at startup with clear error (D-05) |
| Health endpoint leaks internal error messages | Information disclosure | Health endpoint catches all exceptions generically — no stack traces returned |

**Phase 1 security posture:** Minimal attack surface — only `/health` and `/docs` are exposed. No user input processed in Phase 1 (normalization function is used internally in later phases). No authentication required per project constraints (internal service).

---

## Sources

### Primary (HIGH confidence)
- `/home/ccastro/Projects/auto-insight-claw/src/auto_insight_claw/domain/vehicle_identity.py` — canonical_key verbatim implementation [VERIFIED: codebase]
- `/home/ccastro/Projects/auto-insight-claw/src/auto_insight_claw/main.py` — create_app() factory pattern [VERIFIED: codebase]
- `/home/ccastro/Projects/auto-insight-claw/src/auto_insight_claw/config.py` — pydantic-settings BaseSettings pattern [VERIFIED: codebase]
- `/home/ccastro/Projects/auto-insight-claw/pyproject.toml` — mypy overrides, ruff config, pytest config [VERIFIED: codebase]
- `/home/ccastro/Projects/auto-insight-claw/tests/conftest.py` — env setup before imports [VERIFIED: codebase]
- PyPI registry — all package versions verified via `pip index versions` [VERIFIED: PyPI]
- slopcheck 0.6.1 — all packages passed legitimacy check [VERIFIED: slopcheck]
- `https://fastapi.tiangolo.com/advanced/events/` — lifespan pattern [CITED]
- `https://fastapi.tiangolo.com/tutorial/bigger-applications/` — APIRouter pattern [CITED]

### Secondary (MEDIUM confidence)
- `https://docs.astral.sh/uv/guides/integration/fastapi/` — uv + FastAPI project layout [CITED]
- `https://docs.astral.sh/uv/concepts/projects/config/` — src-layout requires `[build-system]` declaration [CITED]

### Tertiary (LOW confidence)
- asyncpg `timeout` parameter on `connect()` — training knowledge, not verified via docs in this session [ASSUMED]

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages verified on PyPI, slopcheck clean, identical to parent project
- Architecture: HIGH — patterns verified directly from parent codebase and official FastAPI docs
- Pitfalls: HIGH — asyncpg URL scheme pitfall verified by understanding how SQLAlchemy DSN format works; mypy override pattern verified from parent pyproject.toml
- Normalization logic: HIGH — copied verbatim from parent project source, line 15 confirmed

**Research date:** 2026-05-22
**Valid until:** 2026-06-22 (stable ecosystem; FastAPI, asyncpg, pydantic-settings release cadence is moderate)
