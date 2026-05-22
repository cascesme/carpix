# Phase 2: Storage Layer - Pattern Map

**Mapped:** 2026-05-22
**Files analyzed:** 5 (3 new, 2 modified)
**Analogs found:** 5 / 5

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/carpix_images/config.py` (modify) | config | — | `src/carpix_images/config.py` (Phase 1, actual) | exact — add one field |
| `src/carpix_images/services/__init__.py` (create) | config | — | `src/carpix_images/domain/__init__.py` (empty init) | exact |
| `src/carpix_images/services/storage.py` (create) | service | file-I/O | `src/carpix_images/routers/health.py` (async service logic) | role-partial — same async pattern, different I/O |
| `tests/unit/test_storage.py` (create) | test | file-I/O | `tests/unit/test_normalize.py` + `tests/unit/test_health.py` | role-match — class-based + standalone, `-> None`, `tmp_path` fixture |
| `tests/conftest.py` (modify) | test | — | `tests/conftest.py` (Phase 1, actual) | exact — add one `setdefault` line |

---

## Pattern Assignments

### `src/carpix_images/config.py` (modify — add `images_dir` field)

**Analog:** `src/carpix_images/config.py` (lines 1–14, Phase 1 actual)

**Existing file — full content** (lines 1–14):
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

**What to add — import and field** (insert `from pathlib import Path` and `from pydantic import Field` at top; add `images_dir` field after `database_url`):
```python
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    database_url: str
    images_dir: Path = Field(default=Path("/images"))  # NEW in Phase 2


settings = Settings()
```

**Constraints:**
- `Field(default=Path("/images"))` — production default; tests inject `tmp_path` directly to `StorageService`, NOT via env var (so no `IMAGES_DIR` override in unit tests)
- `Path` field type: pydantic-settings coerces `IMAGES_DIR=/tmp/x` env var to `PosixPath('/tmp/x')` automatically
- ruff UP rules: use `from pathlib import Path` directly, NOT `os.PathLike` from typing

---

### `src/carpix_images/services/__init__.py` (create — empty)

**Analog:** `src/carpix_images/domain/__init__.py` (empty file)

**Pattern:** Empty file. No imports, no content. Required for Python package discovery.

```python
```

**Constraint:** Without this file, `from carpix_images.services.storage import StorageService` raises `ModuleNotFoundError` even though `storage.py` exists.

---

### `src/carpix_images/services/storage.py` (create)

**Analog (async pattern):** `src/carpix_images/routers/health.py` (lines 1–20)

**Imports pattern from analog** (lines 1–6):
```python
import asyncpg
from fastapi import APIRouter

from carpix_images.config import settings
```

**Async method pattern from analog** (lines 9–20):
```python
@router.get("/health")
async def health() -> dict[str, str]:
    db_status = "error"
    ...
    try:
        conn = await asyncpg.connect(dsn, timeout=3)
        await conn.execute("SELECT 1")
        await conn.close()
        ...
    except Exception:
        pass
    return {"status": "ok", "db": db_status}
```

**Full target file pattern** (from RESEARCH.md verified skeleton):
```python
# src/carpix_images/services/storage.py
from __future__ import annotations

from pathlib import Path

import anyio
from fastapi.responses import FileResponse


class StorageService:
    def __init__(self, base_dir: Path) -> None:
        self._base = base_dir.resolve()

    def _validated_path(self, brand_key: str, model_key: str, year: int) -> Path:
        candidate = self._base / brand_key / model_key / str(year) / "image.jpg"
        resolved = candidate.resolve()
        if not resolved.is_relative_to(self._base):
            raise ValueError(f"Path traversal attempt: {candidate!r}")
        return resolved

    async def save(self, brand_key: str, model_key: str, year: int, data: bytes) -> Path:
        target_dir = anyio.Path(self._base) / brand_key / model_key / str(year)
        await target_dir.mkdir(parents=True, exist_ok=True)
        target_file = target_dir / "image.jpg"
        await target_file.write_bytes(data)
        return Path(target_file)

    def file_response(self, brand_key: str, model_key: str, year: int) -> FileResponse:
        path = self._validated_path(brand_key, model_key, year)
        return FileResponse(path=path, media_type="image/jpeg")
```

**Key implementation constraints:**
- `__init__` calls `base_dir.resolve()` — resolves symlinks on the base, not just the candidate
- `_validated_path` calls `.resolve()` on the candidate and compares against the already-resolved `self._base` (no double-resolve needed on `self._base` inside this method)
- `save()` uses `anyio.Path` (async) for both `mkdir` and `write_bytes` — NOT `pathlib.Path` which is sync
- `file_response()` is synchronous (`def`, not `async def`) — `FileResponse.__init__` is synchronous; the async I/O happens at ASGI dispatch time
- `str(year)` required in path construction — `pathlib` rejects `int` in the `/` operator
- `StorageService` MUST NOT import or raise `HTTPException` — raise `ValueError` only; router converts to HTTP 400
- `from __future__ import annotations` at top — matches project style (see `domain/normalize.py`)
- ruff UP: use `str | None` not `Optional[str]`, `Path` not `os.PathLike`

---

### `tests/unit/test_storage.py` (create)

**Analog (class structure):** `tests/unit/test_normalize.py` (lines 1–31) + `tests/unit/test_health.py` (lines 1–34)

**Import + class structure pattern from test_normalize.py** (lines 1–5):
```python
"""Unit tests for canonical_key normalization — NORM-01."""

import pytest

from carpix_images.domain.normalize import canonical_key
```

**Class-based test grouping pattern from test_normalize.py** (lines 23–31):
```python
class TestCanonicalKey:
    def test_output_is_lowercase(self) -> None:
        result = canonical_key("Toyota Camry")
        assert result == result.lower()

    def test_dm_i_variants_are_equivalent(self) -> None:
        assert canonical_key("DM-i") == canonical_key("Dmi")
```

**Async test method pattern from test_health.py** (lines 10–16):
```python
def test_health_returns_200_db_ok() -> None:
    mock_conn = AsyncMock()
    with patch("carpix_images.routers.health.asyncpg.connect", return_value=mock_conn):
        client = TestClient(create_app())
        response = client.get("/health")
    assert response.status_code == 200
```

**Full target file pattern** (from RESEARCH.md verified skeleton):
```python
# tests/unit/test_storage.py
from __future__ import annotations

from pathlib import Path

import pytest

from carpix_images.services.storage import StorageService


class TestStorageServiceSave:
    async def test_save_writes_file_at_correct_path(self, tmp_path: Path) -> None:
        svc = StorageService(tmp_path)
        await svc.save("toyota", "camry", 2020, b"FAKE_JPEG")
        expected = tmp_path / "toyota" / "camry" / "2020" / "image.jpg"
        assert expected.exists()
        assert expected.read_bytes() == b"FAKE_JPEG"

    async def test_save_creates_intermediate_directories(self, tmp_path: Path) -> None:
        svc = StorageService(tmp_path)
        await svc.save("byddmi", "sealudmi", 2023, b"DATA")
        assert (tmp_path / "byddmi" / "sealudmi" / "2023").is_dir()

    async def test_save_is_idempotent(self, tmp_path: Path) -> None:
        svc = StorageService(tmp_path)
        await svc.save("toyota", "camry", 2020, b"FIRST")
        await svc.save("toyota", "camry", 2020, b"SECOND")
        result = (tmp_path / "toyota" / "camry" / "2020" / "image.jpg").read_bytes()
        assert result == b"SECOND"


class TestStorageServiceFileResponse:
    def test_valid_path_returns_file_response(self, tmp_path: Path) -> None:
        from fastapi.responses import FileResponse
        svc = StorageService(tmp_path)
        (tmp_path / "toyota" / "camry" / "2020").mkdir(parents=True)
        (tmp_path / "toyota" / "camry" / "2020" / "image.jpg").write_bytes(b"DATA")
        resp = svc.file_response("toyota", "camry", 2020)
        assert isinstance(resp, FileResponse)

    def test_traversal_attempt_raises_value_error(self, tmp_path: Path) -> None:
        svc = StorageService(tmp_path)
        with pytest.raises(ValueError, match="traversal"):
            svc.file_response("..", "..", 2020)
```

**Key test constraints:**
- `async def test_*` methods within classes — `asyncio_mode = "auto"` in `pyproject.toml` means no `@pytest.mark.asyncio` decorator needed
- `tmp_path: Path` fixture — built into pytest, provides an isolated temporary directory per test
- `-> None` return type annotation on ALL test methods/functions — required by `mypy --strict`
- `from __future__ import annotations` at top — matches project style
- `TestStorageServiceSave` groups all `save()` tests; `TestStorageServiceFileResponse` groups all `file_response()` tests — mirrors `TestCanonicalKey` grouping in `test_normalize.py`
- No mocking needed — `StorageService` takes `base_dir: Path` as a constructor argument; `tmp_path` IS the test base dir

---

### `tests/conftest.py` (modify — add `IMAGES_DIR` setdefault)

**Analog:** `tests/conftest.py` (lines 1–6, Phase 1 actual)

**Existing file — full content** (lines 1–6):
```python
import os

# Must run before any carpix_images module — Settings() reads env at import time.
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/testdb"
)
```

**What to add** (append after existing `setdefault` block):
```python
import os

# Must run before any carpix_images module — Settings() reads env at import time.
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/testdb"
)
os.environ.setdefault("IMAGES_DIR", "/tmp/carpix_test_images")  # NEW in Phase 2
```

**Constraints:**
- Comment must stay at top — explains the import-time side effect
- `IMAGES_DIR` is only needed for integration tests that import `settings.images_dir`; unit tests inject `tmp_path` directly into `StorageService.__init__` and never read `settings.images_dir`
- Use `/tmp/carpix_test_images` (not a `tmp_path`) because `conftest.py` runs at collection time, before pytest fixtures are resolved

---

## Shared Patterns

### Async Method Convention
**Source:** `src/carpix_images/routers/health.py` lines 9–20
**Apply to:** `StorageService.save()` in `services/storage.py`
```python
async def health() -> dict[str, str]:
    ...
    conn = await asyncpg.connect(dsn, timeout=3)
    await conn.execute("SELECT 1")
    await conn.close()
    ...
```
Every async call uses `await`. `anyio.Path.mkdir()` and `anyio.Path.write_bytes()` follow the same pattern.

### Module-Level Singleton
**Source:** `src/carpix_images/config.py` line 14
**Apply to:** `services/storage.py` optional module-level instance
```python
settings = Settings()  # module-level — crashes at startup if DATABASE_URL missing
```
For Phase 2, `StorageService` is instantiated per-call or as a module-level singleton. RESEARCH.md recommends `StorageService(settings.images_dir)` at module level — follow the same convention as `settings = Settings()`.

### `from __future__ import annotations` Header
**Source:** `src/carpix_images/domain/normalize.py` line 1
**Apply to:** `services/storage.py` and `tests/unit/test_storage.py`
```python
from __future__ import annotations
```
All new modules follow this header convention.

### `-> None` Return Types on Tests
**Source:** `tests/unit/test_normalize.py` lines 19, 24, 28 and `tests/unit/test_health.py` lines 10, 19, 30
**Apply to:** All test functions/methods in `tests/unit/test_storage.py`
```python
def test_something(self) -> None:
    ...

async def test_something_async(self, tmp_path: Path) -> None:
    ...
```

### Test Environment Guard
**Source:** `tests/conftest.py` lines 1–6
**Apply to:** Addition to `tests/conftest.py` — maintain the same guard pattern
```python
import os
# Must run before any carpix_images module — Settings() reads env at import time.
os.environ.setdefault("KEY", "value")
```

---

## No Analog Found

All files have direct analogs in the Phase 1 carpix codebase. No files require falling back
to external patterns from RESEARCH.md only — all RESEARCH.md patterns are consistent with
and extend the Phase 1 actual implementation.

---

## Metadata

**Analog search scope:**
- `/home/ccastro/Projects/carpix/src/carpix_images/` — all Phase 1 source files
- `/home/ccastro/Projects/carpix/tests/` — all Phase 1 test files

**Files scanned:** 7
- `src/carpix_images/config.py`
- `src/carpix_images/main.py`
- `src/carpix_images/domain/normalize.py`
- `src/carpix_images/routers/health.py`
- `tests/conftest.py`
- `tests/unit/test_normalize.py`
- `tests/unit/test_health.py`

**Pattern extraction date:** 2026-05-22
