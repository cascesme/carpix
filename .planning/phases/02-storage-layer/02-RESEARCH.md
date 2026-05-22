# Phase 2: Storage Layer - Research

**Researched:** 2026-05-22
**Domain:** Python filesystem I/O, FastAPI FileResponse, path traversal security, async pathlib
**Confidence:** HIGH

## Summary

Phase 2 is a pure Python implementation phase with no new external dependencies. The entire
storage layer is built on stdlib (`pathlib.Path`), FastAPI's built-in `FileResponse`, and
`anyio.Path` (a transitive dependency already present via starlette/FastAPI). No new packages
are required.

The two requirements (STORE-01 and STORE-02) map to two responsibilities in a single
`StorageService` class: (1) write image bytes to the canonical filesystem path, creating
intermediate directories as needed; and (2) compute and validate that a requested file path
resolves within the base images directory before constructing a `FileResponse`. The guard is
enforced using `Path.resolve().is_relative_to(base)`, which Python 3.9+ provides natively and
which correctly collapses `..` segments before comparison.

The only configuration change required in this phase is adding `images_dir: Path` to
`Settings` in `config.py`. This follows the Phase 1 CONTEXT.md directive (D-06) that says
settings are added in their respective phases. The setting carries a default of
`Path('/images')` for production use; tests inject a `tmp_path` directly as a constructor
argument, so no env-var override is required in unit tests.

**Primary recommendation:** Implement `StorageService` in
`src/carpix_images/services/storage.py` with two async public methods — `save()` and
`file_response()` — injecting `base_dir: Path` via `__init__` for testability. The traversal
guard lives inside `file_response()` and raises `ValueError`; the calling router converts it
to an HTTP 400.

## Project Constraints (from CLAUDE.md)

| Directive | Impact on Phase 2 |
|-----------|-------------------|
| Tech stack: FastAPI (Python, async) | StorageService methods must be async |
| Storage: `/images/{brand_key}/{model_key}/{year}/image.jpg` | Exact path contract for `save()` |
| Image width: 800px via Wikimedia CDN only (no PIL/Pillow) | No image resizing in this phase |
| Error handling: always 404, never 500 | Path traversal raises ValueError, not 500 |
| TDD: tests first, ruff + mypy clean | Wave 0 test stubs required before implementation |
| No PIL/Pillow | Storage is raw bytes write-through — no image processing |

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| STORE-01 | Images stored at `/images/{brand_key}/{model_key}/{year}/image.jpg`; directories created on first write | `anyio.Path.mkdir(parents=True, exist_ok=True)` + `write_bytes()` — verified working |
| STORE-02 | Path traversal guard enforced on all `FileResponse` paths — resolved path must pass `is_relative_to(BASE_IMAGES_DIR)` before serving | `Path.resolve().is_relative_to(base)` — verified against `..` traversal attempts |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Image byte persistence (STORE-01) | Backend service layer | — | `StorageService.save()` owns filesystem write; no HTTP concern |
| Directory creation (STORE-01) | Backend service layer | — | Side-effect of `save()`, encapsulated in service |
| Path traversal guard (STORE-02) | Backend service layer | — | Security check belongs in service, not router (SOLID SRP) |
| FileResponse construction (STORE-02) | Backend service layer | Router | Service builds the safe `FileResponse`; router calls it |
| IMAGES_DIR configuration | Config layer | — | `pydantic-settings` `Settings.images_dir: Path` with default |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `pathlib.Path` | stdlib | Path construction, traversal guard, directory creation | Zero-dependency, Python 3.9+ `is_relative_to` covers the full guard |
| `anyio.Path` | 4.13.0 | Async `mkdir` and `write_bytes` without blocking the event loop | Already a transitive dependency of starlette; ships with `py.typed`; no new install |
| `fastapi.responses.FileResponse` | starlette 1.0.0 | Stream the local JPEG file as an async HTTP response | Built into FastAPI; uses anyio internally; no `aiofiles` needed |

[VERIFIED: pip index] `anyio` 4.13.0 — installed as transitive dep of fastapi/starlette.
[VERIFIED: pip index] `starlette` 1.0.0 — installed; `FileResponse` source confirmed to use anyio, not aiofiles.

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pydantic-settings` | 2.14.1+ | `IMAGES_DIR` env var / config | Add `images_dir: Path` field to existing `Settings` class |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `anyio.Path.write_bytes()` | `aiofiles.open()` | `aiofiles` is not in `pyproject.toml` and is not a transitive dep; `anyio.Path` is equivalent and already present |
| `anyio.Path.write_bytes()` | `pathlib.Path.write_bytes()` (sync) | Sync write blocks the event loop for ~200KB; acceptable but `anyio.Path` is the correct async-native choice for a FastAPI service |
| `Path.is_relative_to()` | `try: path.relative_to(base)` | Both work on Python 3.9+; `is_relative_to()` is more readable and does not rely on exception flow for control logic |

**Installation:** No new packages required. Phase 2 uses only transitive dependencies already present.

**Version verification (run before implementing):**
```bash
python3 -c "import importlib.metadata; print(importlib.metadata.version('anyio'))"
python3 -c "import importlib.metadata; print(importlib.metadata.version('starlette'))"
```

## Package Legitimacy Audit

Phase 2 introduces **no new external packages**. All dependencies used (`anyio`, `starlette`,
`pathlib`) are either stdlib or transitive dependencies of `fastapi` already declared in
`pyproject.toml`.

| Package | Registry | Status | Disposition |
|---------|----------|--------|-------------|
| `anyio` | PyPI | Transitive dep of fastapi/starlette — already installed | Approved (no new install) |
| `starlette` | PyPI | Transitive dep of fastapi — already installed | Approved (no new install) |
| `pathlib` | stdlib | Python standard library | Approved |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
  Caller (Phase 5 ImageService)
          |
          | brand_key, model_key, year, image_bytes
          v
  ┌─────────────────────┐
  │   StorageService    │
  │   (services/)       │
  │                     │
  │  save()             │──── anyio.Path.mkdir(parents, exist_ok) ──► /images/…/…/…/
  │    └── write_bytes  │──── anyio.Path.write_bytes()            ──► /images/…/…/…/image.jpg
  │                     │
  │  file_response()    │──── Path.resolve().is_relative_to(base) ──► guard check
  │    └── FileResponse │──► FastAPI FileResponse(path, media_type="image/jpeg")
  └─────────────────────┘
          |
          | ValueError (traversal) → router converts to HTTP 400
          | FileResponse            → router returns directly
          v
       HTTP Router (Phase 6)
```

### Recommended Project Structure
```
src/carpix_images/
├── config.py          # add images_dir: Path field (existing file)
├── main.py            # no changes needed in Phase 2
├── domain/
│   └── normalize.py   # unchanged
├── routers/
│   └── health.py      # unchanged
└── services/          # NEW in Phase 2
    ├── __init__.py    # empty
    └── storage.py     # StorageService class

tests/
├── conftest.py        # add IMAGES_DIR env setdefault (minor update)
└── unit/
    └── test_storage.py  # NEW: unit tests for StorageService
```

### Pattern 1: Async Directory Creation + File Write (STORE-01)

**What:** Creates the full directory hierarchy then writes image bytes atomically.
**When to use:** On every cache-miss write in Phase 5 (called by `ImageService.save()`).

```python
# Source: anyio docs + verified locally 2026-05-22
import anyio
from pathlib import Path

async def save(self, brand_key: str, model_key: str, year: int, data: bytes) -> Path:
    target_dir = anyio.Path(self._base) / brand_key / model_key / str(year)
    await target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / "image.jpg"
    await target_file.write_bytes(data)
    return Path(target_file)  # return pathlib.Path (os.PathLike[str]) for FileResponse compatibility
```

Key properties verified:
- `parents=True`: creates all intermediate directories in one call [VERIFIED: locally]
- `exist_ok=True`: idempotent — second call for same path does not raise [VERIFIED: locally]
- `write_bytes()` overwrites any existing file silently (correct cache-miss behavior) [VERIFIED: locally]

### Pattern 2: Path Traversal Guard (STORE-02)

**What:** Resolves the candidate path to its absolute real path, then checks it is a child of the base directory.
**When to use:** In `file_response()` before constructing `FileResponse`.

```python
# Source: Python stdlib docs + verified locally 2026-05-22
from pathlib import Path

def _validated_path(self, brand_key: str, model_key: str, year: int) -> Path:
    candidate = self._base / brand_key / model_key / str(year) / "image.jpg"
    resolved = candidate.resolve()
    if not resolved.is_relative_to(self._base.resolve()):
        raise ValueError(f"Path traversal attempt: {candidate!r}")
    return resolved
```

Verified behavior [VERIFIED: locally]:
- `/images/toyota/camry/2020/image.jpg` → `is_relative_to('/images')` → `True` (safe)
- `/images/../etc/passwd` → resolves to `/etc/passwd` → `is_relative_to('/images')` → `False` (blocked)
- `/images/../../etc/shadow` → resolves to `/etc/shadow` → blocked
- `/tmp/evil.jpg` → blocked

Important: call `.resolve()` on BOTH sides (`candidate.resolve()` and `self._base.resolve()`)
to handle symlinks in the base directory itself.

### Pattern 3: FileResponse Construction

**What:** Return a `FileResponse` from the validated path with explicit `media_type`.
**When to use:** After path is validated by `_validated_path()`.

```python
# Source: FastAPI official docs https://fastapi.tiangolo.com/advanced/custom-response/
from fastapi.responses import FileResponse
from pathlib import Path

def file_response(self, brand_key: str, model_key: str, year: int) -> FileResponse:
    path = self._validated_path(brand_key, model_key, year)
    return FileResponse(path=path, media_type="image/jpeg")
```

`FileResponse` constructor verified signature [VERIFIED: starlette 1.0.0 source]:
- `path: str | os.PathLike[str]` — accepts `pathlib.Path` directly (Path IS os.PathLike)
- `media_type: str | None` — always pass `"image/jpeg"` explicitly (don't rely on filename inference)
- Automatically adds `Content-Length`, `Last-Modified`, `ETag` headers
- Uses `anyio.to_thread.run_sync(os.stat, path)` internally — raises `RuntimeError` if file missing

### Pattern 4: Settings Extension (config.py update)

**What:** Add `IMAGES_DIR` to `Settings` following Phase 1 convention.
**When to use:** Phase 2 activates this setting.

```python
# Extends src/carpix_images/config.py (Phase 1 pattern)
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

Verified: `Path` field with `Field(default=...)` works with pydantic-settings and env var
override (`IMAGES_DIR=/tmp/test` correctly coerces to `PosixPath('/tmp/test')`). [VERIFIED: locally]

### Anti-Patterns to Avoid

- **Sync write_bytes in async service:** `pathlib.Path.write_bytes()` is synchronous and blocks
  the event loop during the write. Use `anyio.Path.write_bytes()` instead for a FastAPI async
  service. For a ~200KB JPEG the block is brief, but `anyio.Path` is available and correct.

- **Guard with string prefix check:** `str(path).startswith('/images')` is bypassable via
  encoded characters or symlinks. Always use `Path.resolve().is_relative_to(base.resolve())`.

- **Constructing FileResponse before the guard:** The guard must run before `FileResponse` is
  constructed. `FileResponse.__init__` does not perform the guard — it just stores the path.
  The runtime error (if file missing) happens during `__call__` (ASGI dispatch), not at
  construction time.

- **Raising HTTPException from the service layer:** `StorageService` must not import or raise
  `HTTPException`. That couples the service to HTTP. Raise `ValueError`; let the router convert
  it to `HTTPException(status_code=400)`.

- **Not resolving the base directory:** `self._base.resolve()` must be called, not just
  `candidate.resolve()`, because the base itself could be a symlink in Docker volumes.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Async file serving | Custom async generator streaming files | `FileResponse` | Starlette handles `Content-Length`, `Last-Modified`, `ETag`, HTTP range requests, HEAD handling automatically |
| Async directory creation | `os.makedirs` in `asyncio.create_task` | `anyio.Path.mkdir(parents=True, exist_ok=True)` | Correct async-native approach; already a transitive dep |
| Path traversal guard | Custom regex on path string | `Path.resolve().is_relative_to()` | String approach misses encoded sequences and symlinks; stdlib method is authoritative |

**Key insight:** `FileResponse` in starlette 1.0.0 uses `anyio.to_thread.run_sync` internally
for the `os.stat` call, so it is already async-safe. There is no need to add `aiofiles` or
any other async file library.

## Common Pitfalls

### Pitfall 1: Forgetting to resolve both sides of is_relative_to
**What goes wrong:** `Path('/images/test').is_relative_to(Path('/images'))` passes, but
`Path('/images/test').is_relative_to(Path('/images/'))` (trailing slash) or a symlinked
base also passes correctly — but only if `.resolve()` is called on the base too.
**Why it happens:** `is_relative_to` works on the literal path components, not the filesystem
reality. If `/images` is itself a symlink to `/mnt/data/images`, the check fails without
`self._base.resolve()`.
**How to avoid:** Always `candidate.resolve().is_relative_to(self._base.resolve())`.
**Warning signs:** Tests pass locally but fail in Docker where `/images` is a bind-mounted volume.

### Pitfall 2: FileResponse RuntimeError on missing file
**What goes wrong:** `FileResponse(path=path)` at construction time succeeds even if the file
does not exist. The `RuntimeError("File at path X does not exist.")` is raised during ASGI
`__call__`, which FastAPI does not automatically convert to a 404 — it becomes a 500.
**Why it happens:** `FileResponse.__init__` only stores the path; the `os.stat` happens at
dispatch time.
**How to avoid:** For Phase 2 (pure storage service), this is acceptable because `file_response()`
is only called after confirming the path is valid (Phase 5 will add the DB-hit check). Document
that callers must not call `file_response()` on a path that may not exist on disk.
**Warning signs:** Integration tests that call `file_response()` on a non-existent path produce
500s instead of 404s.

### Pitfall 3: year as str vs int in path construction
**What goes wrong:** `Path('/images') / 'toyota' / 'camry' / 2020` raises `TypeError` because
`pathlib` does not accept `int` in `/` operator.
**Why it happens:** Year comes in as `int` from the router path parameter but Path requires str.
**How to avoid:** Always `str(year)` in path construction: `self._base / brand_key / model_key / str(year) / "image.jpg"`.
**Warning signs:** `TypeError: argument should be str or an os.PathLike object, not 'int'`.

### Pitfall 4: Missing `__init__.py` in services/
**What goes wrong:** `from carpix_images.services.storage import StorageService` raises
`ModuleNotFoundError` even though the file exists.
**Why it happens:** `services/` is a new subdirectory that requires `__init__.py` to be a
Python package.
**How to avoid:** Wave 0 must create `src/carpix_images/services/__init__.py` (empty).
**Warning signs:** `ModuleNotFoundError: No module named 'carpix_images.services'`.

### Pitfall 5: ruff UP006/UP035 on type annotations
**What goes wrong:** ruff UP rules flag `typing.Optional`, `List`, `Dict`, `os.PathLike`
import from `typing` rather than `collections.abc` or direct `pathlib.Path`.
**Why it happens:** `ruff select = ["UP"]` in the project config enforces Python 3.12 modern
annotations.
**How to avoid:** Use `Path` directly (from `pathlib`), `str | None` instead of
`Optional[str]`, and `collections.abc.X` for abstract types.

## Code Examples

Verified patterns from official sources and local verification:

### Complete StorageService skeleton (for Wave 1 implementation)
```python
# src/carpix_images/services/storage.py
# Source: pathlib stdlib + anyio 4.x + starlette FileResponse — verified 2026-05-22
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

### Unit test skeleton (for Wave 0 stubs)
```python
# tests/unit/test_storage.py
# Source: pytest + pytest-asyncio asyncio_mode=auto — verified pattern
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

### conftest.py addition (tests/conftest.py)
```python
# Add IMAGES_DIR default for integration tests (after existing DATABASE_URL line)
import os
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/testdb"
)
os.environ.setdefault("IMAGES_DIR", "/tmp/carpix_test_images")  # NEW in Phase 2
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `aiofiles` for async file writes | `anyio.Path.write_bytes()` | anyio 3.x (2021) | `anyio` is already present as a transitive dep; no extra install |
| `os.path` string manipulation for path guard | `Path.resolve().is_relative_to()` | Python 3.9 (2020) | Stdlib method handles symlinks and `..` correctly |
| `@app.on_event("startup")` for lifespan | `@asynccontextmanager lifespan` | FastAPI 0.95 (2023) | Already used in Phase 1 `main.py` |

**Deprecated/outdated:**
- `aiofiles`: Not deprecated, but unnecessary here — `anyio.Path` covers async writes and is already present.
- `os.makedirs()`: Works but is synchronous; use `anyio.Path.mkdir(parents=True, exist_ok=True)`.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `StorageService` will be called with pre-normalized `brand_key`/`model_key` (output of `canonical_key()`) | Architecture Patterns | If called with raw strings, the path guard still catches traversal attempts; functional impact is path varies by caller convention |
| A2 | `file_response()` is synchronous (no `async def`) because `FileResponse.__init__` is synchronous | Code Examples | If anyio.Path resolution were async, the method would need `async def`; confirmed synchronous via starlette 1.0.0 source inspection |

**Both claims are low-risk based on verified source inspection.**

## Open Questions

1. **Should `StorageService` be instantiated once at app startup (singleton) or per-request?**
   - What we know: Phase 5 (ImageService) will depend on StorageService. Phase 3 wires the DB pool as a lifespan-scoped singleton.
   - What's unclear: Whether Phase 5 expects StorageService from DI (FastAPI `Depends`) or direct construction.
   - Recommendation: For Phase 2, construct `StorageService(settings.images_dir)` as a module-level singleton in `services/storage.py`. Phase 5 can refactor to `Depends` if needed. This keeps Phase 2 simple and self-contained.

2. **Should `file_response()` check that the file exists before returning FileResponse?**
   - What we know: `FileResponse` raises `RuntimeError` at dispatch time (not at construction) if the file is missing.
   - What's unclear: Phase 2 success criteria say "a valid path that resolves inside `/images` is served without error" — this implies the file exists when `file_response()` is called. Phase 4/5 will ensure DB-hit implies file exists.
   - Recommendation: Phase 2 does NOT add a pre-existence check. That belongs in Phase 5's self-healing logic (CACHE-04). Document the contract: `file_response()` callers are responsible for ensuring the file exists.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12+ | `Path.is_relative_to()`, type hints | ✓ | 3.13.6 | — |
| `anyio` | `anyio.Path.mkdir`, `write_bytes` | ✓ | 4.13.0 (transitive dep) | — |
| `starlette` | `FileResponse` | ✓ | 1.0.0 (transitive dep) | — |
| `pathlib` | Path construction and guard | ✓ | stdlib | — |

**Missing dependencies with no fallback:** none — all required capabilities are available.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 + pytest-asyncio 1.3.0 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (`asyncio_mode = "auto"`) |
| Quick run command | `python3 -m pytest tests/unit/test_storage.py -x -q` |
| Full suite command | `python3 -m pytest tests/ -x -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| STORE-01 | `save()` writes bytes to `/images/{brand}/{model}/{year}/image.jpg` | unit | `python3 -m pytest tests/unit/test_storage.py::TestStorageServiceSave -x` | ❌ Wave 0 |
| STORE-01 | `save()` creates intermediate directories automatically | unit | `python3 -m pytest tests/unit/test_storage.py::TestStorageServiceSave::test_save_creates_intermediate_directories -x` | ❌ Wave 0 |
| STORE-01 | `save()` is idempotent (second write overwrites first) | unit | `python3 -m pytest tests/unit/test_storage.py::TestStorageServiceSave::test_save_is_idempotent -x` | ❌ Wave 0 |
| STORE-02 | Traversal attempt raises `ValueError` | unit | `python3 -m pytest tests/unit/test_storage.py::TestStorageServiceFileResponse::test_traversal_attempt_raises_value_error -x` | ❌ Wave 0 |
| STORE-02 | Valid path inside base dir returns `FileResponse` | unit | `python3 -m pytest tests/unit/test_storage.py::TestStorageServiceFileResponse::test_valid_path_returns_file_response -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `python3 -m pytest tests/unit/test_storage.py -x -q`
- **Per wave merge:** `python3 -m pytest tests/ -x -q && python3 -m ruff check src/ tests/ && python3 -m mypy src/`
- **Phase gate:** Full suite green + ruff clean + mypy --strict clean before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/unit/test_storage.py` — failing stubs covering all 5 test cases above
- [ ] `src/carpix_images/services/__init__.py` — empty package init (required for import)
- [ ] `src/carpix_images/services/storage.py` — `StorageService` class stub (fails tests)

*(No new framework install required — existing pytest + pytest-asyncio infrastructure covers all tests)*

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | yes | Path traversal guard: `Path.resolve().is_relative_to(base)` |
| V5 Input Validation | yes | `brand_key`, `model_key` validated by `canonical_key()` (Phase 1); year as `int` from router |
| V6 Cryptography | no | — |

### Known Threat Patterns for Filesystem Path Construction

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via `../` in brand/model/year | Tampering / Information Disclosure | `Path.resolve().is_relative_to(base.resolve())` — collapses `..` before comparison |
| Symlink escape (symlink inside `/images` pointing outside) | Tampering | `candidate.resolve()` follows symlinks, so the resolved path would point outside base and be blocked |
| Null byte injection (`brand\x00malicious`) | Tampering | `canonical_key()` strips non-alphanumeric characters, eliminating null bytes before they reach StorageService |

**Defense note:** Although `canonical_key()` makes traversal via brand/model/year inputs
practically impossible in normal request flow, STORE-02 requires the guard to be enforced
unconditionally so that `StorageService` is safe even if called directly with non-normalized
inputs (e.g., during testing, scripting, or future refactoring).

## Sources

### Primary (HIGH confidence)
- Python stdlib docs — `pathlib.Path.is_relative_to`, `pathlib.Path.resolve`, `pathlib.Path.mkdir` — Python 3.9+
- anyio 4.x — `anyio.Path` (`mkdir`, `write_bytes`) — verified via local execution + `py.typed` confirmation
- FastAPI official docs `https://fastapi.tiangolo.com/advanced/custom-response/` — `FileResponse` constructor parameters
- starlette 1.0.0 source (local) — `FileResponse.__init__` and `__call__` implementation; confirmed `anyio` usage, no `aiofiles`

### Secondary (MEDIUM confidence)
- Phase 1 CONTEXT.md + PATTERNS.md — established module structure, config conventions, test patterns
- Phase 1 implementation (src/carpix_images/) — confirmed working patterns for `config.py`, `main.py`, test layout

### Tertiary (LOW confidence)
- None — all claims in this research are verified or cited.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries are verified installed transitive dependencies; no new packages
- Architecture: HIGH — StorageService design directly derived from requirements + verified Python stdlib behavior
- Pitfalls: HIGH — all pitfalls verified via local execution or starlette source inspection

**Research date:** 2026-05-22
**Valid until:** 2026-08-22 (stable APIs — pathlib stdlib, anyio 4.x, starlette 1.x)
