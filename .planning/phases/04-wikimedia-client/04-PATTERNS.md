# Phase 4: Wikimedia Client - Pattern Map

**Mapped:** 2026-05-24
**Files analyzed:** 3 new/modified files
**Analogs found:** 3 / 3

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/carpix_images/services/wikimedia.py` | service | request-response | `src/carpix_images/infrastructure/cache_repository.py` | role-match (same DI constructor pattern, same `async` method shape, same `| None` sentinel return) |
| `tests/unit/test_wikimedia.py` | test | request-response | `tests/unit/test_storage.py` | exact (same unit test layout, same `asyncio_mode="auto"` pytest config, same class-free async test style) |
| `pyproject.toml` | config | — | `pyproject.toml` (self) | exact (move `httpx` from dev extras to `[project].dependencies`) |

---

## Pattern Assignments

### `src/carpix_images/services/wikimedia.py` (service, request-response)

**Analog:** `src/carpix_images/infrastructure/cache_repository.py`

**Imports pattern** (lines 1-7 of analog):
```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine
```

Apply the same `from __future__ import annotations` header and bare-module-level constants pattern. For `wikimedia.py` the equivalent is:
```python
from __future__ import annotations

import httpx

_COMMONS_API = "https://commons.wikimedia.org/w/api.php"
_USER_AGENT = "carpix-images/0.1 (https://github.com/user/carpix)"
```

**Dependency-injection constructor pattern** (lines 22-23 of analog):
```python
class CacheRepository:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine
```

Apply identically — swap `AsyncEngine` for `httpx.AsyncClient`:
```python
class WikimediaClient:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client
```

**Async method with `| None` return pattern** (lines 26-51 of analog):
```python
async def find(
    self, brand_key: str, model_key: str, year: int
) -> CacheEntry | None:
    async with self._engine.connect() as conn:
        result = await conn.execute(...)
        row = result.fetchone()
    if row is None:
        return None
    return CacheEntry(...)
```

Apply the same `str | None` return type (Python 3.12+, no `Optional`) and the pattern of returning `None` as a sentinel — never raising on empty result. The `find_jpeg_url` and `_search_first_jpeg` methods follow this exact sentinel contract.

**Error handling pattern** (health router analog — `src/carpix_images/routers/health.py` lines 13-19):
```python
try:
    conn = await asyncpg.connect(dsn, timeout=3)
    await conn.execute("SELECT 1")
    await conn.close()
    db_status = "ok"
except Exception:
    pass
```

For `wikimedia.py`: use `response.raise_for_status()` to propagate HTTP errors upward to the caller. The caller (Phase 5 ImageService) decides how to map failures to HTTP responses. Do not swallow `httpx.HTTPStatusError` inside `WikimediaClient` — let it propagate.

**JSON safe-navigation pattern** (from RESEARCH.md Pattern 1, lines 205-209):
```python
pages = data.get("query", {}).get("pages", {})
candidates = sorted(pages.values(), key=lambda p: p.get("index", 999))
for page in candidates:
    imageinfo = page.get("imageinfo", [])
    if not imageinfo:
        continue
    info = imageinfo[0]
    if info.get("mime") == "image/jpeg":
        return str(info["thumburl"])
return None
```

Two chained `.get()` calls with empty-dict defaults guard against the `"query"` key being absent entirely (Wikimedia omits it when zero results match).

**mypy strict annotation** (analog: `cache_repository.py` line 64):
```python
async def engine() -> AsyncEngine:  # type: ignore[override]
```

For JSON dict access on `Any`, use:
```python
data: dict = response.json()  # type: ignore[assignment]
```

---

### `tests/unit/test_wikimedia.py` (test, request-response)

**Analog:** `tests/unit/test_storage.py`

**Imports pattern** (lines 1-8 of analog):
```python
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.responses import FileResponse

from carpix_images.services.storage import StorageService
```

Apply same header + import structure for the wikimedia test:
```python
from __future__ import annotations

import httpx
import pytest
import respx

from carpix_images.services.wikimedia import WikimediaClient
```

**Fixture pattern** (test_storage.py uses `tmp_path` builtin; wikimedia uses a local fixture):
```python
# From test_storage.py — fixture used inline as method param:
async def test_save_writes_file_at_correct_path(self, tmp_path: Path) -> None:
    svc = StorageService(tmp_path)
```

For wikimedia, define a module-level fixture (not a class method — test_storage.py uses both styles; prefer module-level for wikimedia since classes add no grouping value here):
```python
@pytest.fixture()
def wiki_client() -> WikimediaClient:
    return WikimediaClient(httpx.AsyncClient())
```

**Async test style** (lines 12-17 of analog — `asyncio_mode = "auto"` is already set in `pyproject.toml` so no decorator needed):
```python
async def test_save_writes_file_at_correct_path(self, tmp_path: Path) -> None:
    svc = StorageService(tmp_path)
    await svc.save("toyota", "camry", 2020, b"FAKE_JPEG")
    expected = tmp_path / "toyota" / "camry" / "2020" / "image.jpg"
    assert expected.exists() is True
```

Apply identically — `async def` test with `await`, no `@pytest.mark.asyncio` decorator (auto mode):
```python
async def test_find_jpeg_url_returns_thumburl(
    wiki_client: WikimediaClient, respx_mock: respx.MockRouter
) -> None:
    respx_mock.get("https://commons.wikimedia.org/w/api.php").respond(
        200, json={...}
    )
    result = await wiki_client.find_jpeg_url("toyota", "corolla", 2022)
    assert result is not None
```

**`pytest.raises` pattern** (lines 41-43 of analog):
```python
def test_traversal_attempt_raises_value_error(self, tmp_path: Path) -> None:
    svc = StorageService(tmp_path)
    with pytest.raises(ValueError, match="traversal"):
        svc.file_response("..", "..", 2020)
```

Apply same `pytest.raises` pattern for the HTTP error test (when `raise_for_status()` fires):
```python
async def test_raises_on_http_error(
    wiki_client: WikimediaClient, respx_mock: respx.MockRouter
) -> None:
    respx_mock.get("https://commons.wikimedia.org/w/api.php").respond(500)
    with pytest.raises(httpx.HTTPStatusError):
        await wiki_client.find_jpeg_url("any", "vehicle", 2020)
```

**respx fixture usage** — `respx_mock` is a pytest fixture provided by the `respx` plugin (no import or registration needed, just declare as parameter). It is sync — register routes synchronously before the async body runs:
```python
async def test_name(
    wiki_client: WikimediaClient, respx_mock: respx.MockRouter
) -> None:
    respx_mock.get("https://commons.wikimedia.org/w/api.php").respond(200, json={...})
    result = await wiki_client.find_jpeg_url(...)
    assert result == "..."
```

**Docstring convention** (from `tests/integration/test_cache_repository.py` lines 1-7):
```python
"""Integration tests for CacheRepository — covers DB-01, DB-02, DB-03.

DB-01: ...
"""
```

Apply same convention — top-of-file docstring naming the phase requirements covered (WIKI-01, WIKI-02, WIKI-03).

---

### `pyproject.toml` (config, dependency move)

**Analog:** `pyproject.toml` itself (self-referential change)

**Current production deps block** (lines 9-15):
```toml
[project]
...
dependencies = [
    "fastapi>=0.136.1",
    "uvicorn[standard]>=0.47.0",
    "pydantic-settings>=2.14.1",
    "asyncpg>=0.31.0",
    "sqlalchemy>=2.0",
]
```

**Current dev extras block** (lines 17-27):
```toml
[project.optional-dependencies]
dev = [
    "pytest>=9.0.3",
    "pytest-asyncio>=1.3.0",
    "httpx>=0.28.1",
    ...
]
```

**Change required:** Move `"httpx>=0.28.1"` from `[project.optional-dependencies].dev` to `[project].dependencies`. This matches the existing pattern for production libraries (`asyncpg`, `sqlalchemy`). Result:
```toml
dependencies = [
    "fastapi>=0.136.1",
    "uvicorn[standard]>=0.47.0",
    "pydantic-settings>=2.14.1",
    "asyncpg>=0.31.0",
    "sqlalchemy>=2.0",
    "httpx>=0.28.1",
]
```

---

## Shared Patterns

### Dependency Injection Constructor
**Source:** `src/carpix_images/infrastructure/cache_repository.py` lines 21-23
**Apply to:** `wikimedia.py`
```python
class CacheRepository:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine
```
Pattern: single external dependency injected at construction, stored as `self._<name>`. Enables test injection without mocking module-level state.

### `from __future__ import annotations` Header
**Source:** Every source file in `src/carpix_images/` (storage.py line 1, cache_repository.py line 1, main.py line 1)
**Apply to:** `wikimedia.py`, `test_wikimedia.py`
```python
from __future__ import annotations
```
All project source files include this as the first line.

### `str | None` Return Sentinel (not `Optional[str]`)
**Source:** `src/carpix_images/infrastructure/cache_repository.py` lines 26-27
```python
async def find(
    self, brand_key: str, model_key: str, year: int
) -> CacheEntry | None:
```
**Apply to:** `WikimediaClient.find_jpeg_url` and `WikimediaClient._search_first_jpeg` — use `str | None`, never `Optional[str]`.

### Async Method with No Decorator
**Source:** `src/carpix_images/services/storage.py` lines 22-24 and `tests/unit/test_storage.py` lines 12-14
**Apply to:** All async methods in `wikimedia.py` and all async test functions in `test_wikimedia.py`
```python
# pyproject.toml: asyncio_mode = "auto" — no @pytest.mark.asyncio needed
async def test_save_writes_file_at_correct_path(self, tmp_path: Path) -> None:
```

### mypy `# type: ignore` for External Library Returns
**Source:** `tests/integration/test_cache_repository.py` lines 64-65
```python
async def engine() -> AsyncEngine:  # type: ignore[override]
    ...
    yield e  # type: ignore[misc]
```
**Apply to:** `wikimedia.py` JSON parsing:
```python
data: dict = response.json()  # type: ignore[assignment]
```

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| — | — | — | All three files have direct analogs in the codebase |

No files in this phase are without a codebase analog. The `WikimediaClient` class structure maps directly to `CacheRepository` (DI constructor, async methods, `| None` sentinel). The test file maps directly to `test_storage.py` (unit tests, `asyncio_mode="auto"`, pytest fixtures). The `pyproject.toml` change is self-referential (same file, same block structure).

---

## Metadata

**Analog search scope:** `src/carpix_images/`, `tests/unit/`, `tests/integration/`, `pyproject.toml`
**Files scanned:** 11 source files + 4 test files + 1 config file
**Pattern extraction date:** 2026-05-24
