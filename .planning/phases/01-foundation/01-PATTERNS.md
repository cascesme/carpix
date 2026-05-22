# Phase 1: Foundation - Pattern Map

**Mapped:** 2026-05-22
**Files analyzed:** 11 new files (greenfield project — no existing carpix source code)
**Analogs found:** 11/11 (all from parent project `/home/ccastro/Projects/auto-insight-claw/`)

---

## Greenfield Note

The carpix repo contains only `CLAUDE.md` and `LICENSE`. Every source file in Phase 1
is created from scratch. All analogs come from the parent project
(`auto-insight-claw`), which is explicitly designated as the reference in
`01-CONTEXT.md` (canonical_refs section). Patterns are extracted verbatim from
those sources.

---

## File Classification

| New File | Role | Data Flow | Closest Analog | Match Quality |
|----------|------|-----------|----------------|---------------|
| `pyproject.toml` | config | — | `/home/ccastro/Projects/auto-insight-claw/pyproject.toml` | exact |
| `src/carpix_images/__init__.py` | config | — | `/home/ccastro/Projects/auto-insight-claw/src/auto_insight_claw/__init__.py` | role-match (empty file) |
| `src/carpix_images/main.py` | config | request-response | `/home/ccastro/Projects/auto-insight-claw/src/auto_insight_claw/main.py` | exact |
| `src/carpix_images/config.py` | config | — | `/home/ccastro/Projects/auto-insight-claw/src/auto_insight_claw/config.py` | exact |
| `src/carpix_images/domain/__init__.py` | config | — | (empty file) | role-match |
| `src/carpix_images/domain/normalize.py` | utility | transform | `/home/ccastro/Projects/auto-insight-claw/src/auto_insight_claw/domain/vehicle_identity.py` | exact (verbatim copy) |
| `src/carpix_images/routers/__init__.py` | config | — | (empty file) | role-match |
| `src/carpix_images/routers/health.py` | route | request-response | `/home/ccastro/Projects/auto-insight-claw/src/auto_insight_claw/main.py` (APIRouter pattern) | role-match |
| `tests/conftest.py` | test | — | `/home/ccastro/Projects/auto-insight-claw/tests/conftest.py` | exact |
| `tests/unit/test_normalize.py` | test | transform | `/home/ccastro/Projects/auto-insight-claw/tests/unit/test_vehicle_identity.py` | exact |
| `tests/unit/test_health.py` | test | request-response | `/home/ccastro/Projects/auto-insight-claw/tests/unit/test_vehicle_identity.py` (structure) | role-match |

---

## Pattern Assignments

### `pyproject.toml` (config)

**Analog:** `/home/ccastro/Projects/auto-insight-claw/pyproject.toml`

**Build system pattern** (lines 1-3):
```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

**Package declaration pattern** (lines 5-9):
```toml
[project]
name = "auto-insight-claw"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [...]
```

**Dev extras pattern** (lines 31-43):
```toml
[project.optional-dependencies]
dev = [
    "pytest>=9.0.3",
    "pytest-asyncio>=1.3.0",
    "mypy>=1.20.2",
    "ruff>=0.15.12",
    "testcontainers[postgres]>=4.14.2",
]
```

**Hatchling src-layout discovery** (line 48-49):
```toml
[tool.hatch.build.targets.wheel]
packages = ["src/auto_insight_claw"]
```

**pytest config pattern** (lines 51-57):
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
pythonpath = ["src"]
```

**mypy strict pattern** (lines 59-64):
```toml
[tool.mypy]
strict = true
python_version = "3.12"
mypy_path = "src"
explicit_package_bases = true
plugins = ["pydantic.mypy"]
```

**mypy overrides pattern — asyncpg** (lines 84-86):
```toml
[[tool.mypy.overrides]]
module = ["asyncpg", "asyncpg.*"]
ignore_missing_imports = true
```

**mypy overrides pattern — pydantic_settings** (lines 71-73):
```toml
[[tool.mypy.overrides]]
module = ["pydantic_settings"]
ignore_missing_imports = true
```

**mypy overrides pattern — testcontainers** (lines 87-89):
```toml
[[tool.mypy.overrides]]
module = ["testcontainers", "testcontainers.*"]
ignore_missing_imports = true
```

**ruff config pattern** (lines 98-103):
```toml
[tool.ruff]
target-version = "py312"
line-length = 88

[tool.ruff.lint]
select = ["E", "F", "I", "UP"]
```

**Adaptation notes for carpix:**
- `name = "carpix-images"`
- `packages = ["src/carpix_images"]`
- Strip all parent-project-specific deps (celery, redis, langchain, etc.)
- Keep only: `fastapi>=0.136.1`, `uvicorn[standard]>=0.47.0`, `pydantic-settings>=2.14.1`, `asyncpg>=0.31.0`
- Dev extras: `pytest`, `pytest-asyncio`, `httpx`, `ruff`, `mypy`, `respx`, `testcontainers[postgres]`
- Remove alembic/celery/langchain mypy overrides; keep asyncpg, pydantic_settings, testcontainers

---

### `src/carpix_images/main.py` (config, request-response)

**Analog:** `/home/ccastro/Projects/auto-insight-claw/src/auto_insight_claw/main.py` (lines 1-41)

**Imports pattern** (lines 1-8):
```python
import sys

from fastapi import FastAPI
from pydantic import ValidationError

from auto_insight_claw.api.router import api_router
from auto_insight_claw.config import Settings, settings
from auto_insight_claw.logging_config import RequestIDMiddleware, configure_logging
```

**App factory pattern** (lines 11-30):
```python
def create_app() -> FastAPI:
    _validate_startup()
    configure_logging(settings.log_format)
    app = FastAPI(
        title="AutoInsight Claw",
        version="1.0.0",
        description=(...),
        contact={"name": "AutoInsight Claw", "email": "autoinsight@gmail.com"},
        license_info={"name": "MIT"},
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url="/redoc" if settings.docs_enabled else None,
    )
    app.add_middleware(RequestIDMiddleware)
    app.include_router(api_router)
    return app
```

**Lifespan pattern** (from RESEARCH.md Pattern 1 — Phase 1 uses no-op lifespan, not on_event):
```python
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

**Adaptation notes for carpix:**
- Remove middleware wiring (RequestIDMiddleware, logging) — Phase 1 has no middleware
- Remove `_validate_startup()` — pydantic-settings crashes at import with a clear ValidationError, no need to double-validate
- Add `lifespan=lifespan` argument to `FastAPI()` — parent project does NOT use lifespan (it predates this CONTEXT.md decision), but CONTEXT.md mandates it
- Import health router from `carpix_images.routers.health`
- Keep `app = create_app()` at module level so uvicorn can find `main:app`

---

### `src/carpix_images/config.py` (config)

**Analog:** `/home/ccastro/Projects/auto-insight-claw/src/auto_insight_claw/config.py` (lines 1-37)

**Full file pattern** (lines 1-37):
```python
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    database_url: str
    redis_url: str
    oriosearch_api_url: str = Field(default="")
    ...

settings = Settings()
```

**Adaptation notes for carpix:**
- Keep `model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)`
- Phase 1 declares ONLY `database_url: str` — no other fields (D-06)
- No `Field()` with defaults — `database_url` is required, crashes at startup if missing (D-05)
- `settings = Settings()` at module level — identical pattern
- No `Field` import needed if no fields use it in Phase 1

**Minimal Phase 1 form:**
```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    database_url: str


settings = Settings()
```

---

### `src/carpix_images/domain/normalize.py` (utility, transform)

**Analog:** `/home/ccastro/Projects/auto-insight-claw/src/auto_insight_claw/domain/vehicle_identity.py` (lines 15-21)

**Verbatim copy — canonical_key function** (lines 1-2, 15-21):
```python
from __future__ import annotations

import re


def canonical_key(value: str) -> str:
    """Compact identity key for cache/coalescing lookups.

    Removes all non-alphanumeric characters and lowercases, so
    'DM-i', 'DMi', 'Dmi', and 'DM i' all map to 'dmi'.
    """
    return re.sub(r"[^a-z0-9]", "", value.lower())
```

**Critical constraint:** Copy ONLY `canonical_key`. Do NOT copy `clean_display`, `canonicalize_pair`, or `normalize_competitors` — these are parent-project-specific and explicitly excluded from Phase 1 per CONTEXT.md specifics.

**Module-level imports for this file:**
- `from __future__ import annotations` — matches parent project style
- `import re` — only stdlib dependency

---

### `src/carpix_images/routers/health.py` (route, request-response)

**No direct analog in parent project** — auto-insight-claw does not have a health router. The pattern is assembled from:
- APIRouter structure: parent project's `api/router.py` conventions
- DB probe logic: RESEARCH.md Pattern 3 (asyncpg + try/except)

**APIRouter import and instantiation pattern** (from parent project router files):
```python
from fastapi import APIRouter

router = APIRouter()
```

**Health endpoint core pattern** (from RESEARCH.md Code Examples, lines 473-493):
```python
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

**Critical behavior constraints:**
- `status` is ALWAYS `"ok"` — unconditional process liveness (D-03)
- `db` is `"ok"` or `"error"` — reflects probe only (D-04)
- `except Exception: pass` — no error details returned to caller (security: no stack traces)
- URL scheme stripping: `replace("postgresql+asyncpg://", "postgresql://")` before `asyncpg.connect()` — prevents `ValueError: invalid dsn` (RESEARCH.md Pitfall 1)
- `timeout=3` on `asyncpg.connect()` — prevents health check from hanging (verify kwarg name against asyncpg docs)

---

### `tests/conftest.py` (test)

**Analog:** `/home/ccastro/Projects/auto-insight-claw/tests/conftest.py` (lines 1-9)

**Full file pattern** (lines 1-9):
```python
import os

# Must run before any auto_insight_claw module — Settings() reads env at import time.
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/testdb"
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("ORIOSEARCH_API_URL", "http://orio-search-api:8000")
os.environ.pop("TAVILY_API_KEY", None)  # retired — Settings() rejects unknown fields
```

**Adaptation notes for carpix:**
- Set only `DATABASE_URL` — the only required setting in Phase 1 (D-06)
- Use `postgresql+asyncpg://` scheme so it matches what Phase 3 SQLAlchemy will expect; health router strips the specifier itself
- Remove all parent-project-specific vars (REDIS_URL, ORIOSEARCH_API_URL, etc.)
- Keep the comment explaining WHY this must run first — critical for test maintainers

**Minimal Phase 1 form:**
```python
import os

# Must run before any carpix_images module — Settings() reads env at import time.
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/testdb"
)
```

---

### `tests/unit/test_normalize.py` (test, transform)

**Analog:** `/home/ccastro/Projects/auto-insight-claw/tests/unit/test_vehicle_identity.py` — `TestCanonicalKey` class (lines 1-51)

**Import and class structure pattern** (lines 1-11):
```python
"""Unit tests for vehicle identity normalization functions."""
from auto_insight_claw.domain.vehicle_identity import (
    canonical_key,
    ...
)


class TestCanonicalKey:
    def test_lowercase(self) -> None:
        assert canonical_key("Toyota") == canonical_key("TOYOTA")
```

**Test method pattern** — individual assertion per behavior (lines 11-51):
```python
def test_strips_whitespace(self) -> None:
    assert canonical_key("  Toyota  ") == canonical_key("Toyota")

def test_dm_i_variants_are_equivalent(self) -> None:
    assert canonical_key("DM-i") == canonical_key("Dmi")
    assert canonical_key("Dmi") == canonical_key("DMi")

def test_alphanumeric_only_in_output(self) -> None:
    result = canonical_key("Seal U DM-i")
    assert result.isalnum()

def test_output_is_lowercase(self) -> None:
    result = canonical_key("Toyota Camry")
    assert result == result.lower()
```

**Adaptation notes for carpix:**
- Change import to `from carpix_images.domain.normalize import canonical_key`
- Keep `class TestCanonicalKey:` class-based grouping — matches parent project style
- Cover all NORM-01 parametrize cases from RESEARCH.md: toyota, byddmi, landrover, alfaromeo, model3, empty string
- Use both class-based single-assertion style (parent project) AND parametrize for the RESEARCH.md required cases
- Return type annotation `-> None` on every test method — required by mypy strict

---

### `tests/unit/test_health.py` (test, request-response)

**Analog:** `/home/ccastro/Projects/auto-insight-claw/tests/unit/test_vehicle_identity.py` — structure only (class-based, `-> None` return types)

**No direct async HTTP router test analog in parent project.** Pattern assembled from:
- RESEARCH.md Code Examples (lines 540-558): mock pattern using `unittest.mock`
- Parent project class structure for grouping

**Test structure pattern** (from RESEARCH.md lines 540-558):
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

**Additional test — docs route** (from RESEARCH.md Validation Architecture):
```python
def test_docs_accessible() -> None:
    client = TestClient(create_app())
    response = client.get("/docs")
    assert response.status_code == 200
```

**Notes:**
- `TestClient` from `fastapi.testclient` (synchronous — no async needed for these tests)
- Patch target MUST be `"carpix_images.routers.health.asyncpg.connect"` — patch where it is USED, not where it is defined
- `AsyncMock()` for the mock connection object — `conn.execute()` and `conn.close()` are both awaited in the router
- `-> None` on all test functions for mypy strict compliance

---

### `src/carpix_images/__init__.py`, `src/carpix_images/domain/__init__.py`, `src/carpix_images/routers/__init__.py`, `tests/__init__.py`, `tests/unit/__init__.py`, `tests/integration/__init__.py` (config)

**Analog:** Standard Python package `__init__.py` convention.

**Pattern:** Empty files. No imports, no content. Required for Python package discovery and pytest collection.

---

## Shared Patterns

### Config Validation at Import Time
**Source:** `/home/ccastro/Projects/auto-insight-claw/src/auto_insight_claw/config.py` line 37
**Apply to:** `src/carpix_images/config.py`
```python
settings = Settings()  # module-level — crashes at startup if DATABASE_URL missing
```

### Test Environment Guard
**Source:** `/home/ccastro/Projects/auto-insight-claw/tests/conftest.py` lines 1-6
**Apply to:** `tests/conftest.py` — must be the FIRST file pytest processes
```python
import os
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/testdb")
```

### mypy Strict + Missing Stubs Pattern
**Source:** `/home/ccastro/Projects/auto-insight-claw/pyproject.toml` lines 59-103
**Apply to:** `pyproject.toml` `[tool.mypy]` section
```toml
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
```

### Ruff Lint Config
**Source:** `/home/ccastro/Projects/auto-insight-claw/pyproject.toml` lines 98-103
**Apply to:** `pyproject.toml` `[tool.ruff]` section
```toml
[tool.ruff]
target-version = "py312"
line-length = 88

[tool.ruff.lint]
select = ["E", "F", "I", "UP"]
```

### pytest asyncio_mode = "auto"
**Source:** `/home/ccastro/Projects/auto-insight-claw/pyproject.toml` line 53
**Apply to:** `pyproject.toml` `[tool.pytest.ini_options]` section
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
pythonpath = ["src"]
```

### Return type annotation `-> None` on all test functions
**Source:** `/home/ccastro/Projects/auto-insight-claw/tests/unit/test_vehicle_identity.py` (all methods)
**Apply to:** All test functions in `tests/unit/`
```python
def test_something(self) -> None:
    ...
```

---

## No Analog Found

None — all patterns have direct analogs in the parent project. The health router has
no exact analog (parent project has no health endpoint) but is assembled from APIRouter
pattern + asyncpg probe pattern, both of which are covered in RESEARCH.md Code Examples
and verified against the parent project's router structure.

---

## Metadata

**Analog search scope:**
- `/home/ccastro/Projects/auto-insight-claw/src/auto_insight_claw/` — source files
- `/home/ccastro/Projects/auto-insight-claw/tests/` — test files
- `/home/ccastro/Projects/auto-insight-claw/pyproject.toml` — build/tool config

**Files scanned from parent project:** 5
- `src/auto_insight_claw/domain/vehicle_identity.py`
- `src/auto_insight_claw/main.py`
- `src/auto_insight_claw/config.py`
- `pyproject.toml`
- `tests/conftest.py`
- `tests/unit/test_vehicle_identity.py`

**Pattern extraction date:** 2026-05-22
