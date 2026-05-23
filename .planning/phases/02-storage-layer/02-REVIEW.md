---
phase: 02-storage-layer
reviewed: 2026-05-23T00:00:00Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - src/carpix_images/services/__init__.py
  - src/carpix_images/services/storage.py
  - tests/unit/test_storage.py
  - tests/conftest.py
  - src/carpix_images/config.py
findings:
  critical: 2
  warning: 2
  info: 2
  total: 6
status: issues_found
---

# Phase 02: Storage Layer — Code Review Report

**Reviewed:** 2026-05-23T00:00:00Z
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found

## Summary

Reviewed the storage service implementation (`StorageService`), its unit tests, the shared test
`conftest.py`, and the application settings module. The service has a clean dependency-injection
design and correct path-traversal protection in its read path. However, the write path (`save()`)
has no traversal check at all, and the read path violates the project's core error-handling
contract (no 500s) by returning a `FileResponse` without verifying the file exists on disk.
These two issues are critical and must be resolved before this layer ships.

---

## Critical Issues

### CR-01: `save()` Has No Path-Traversal Protection

**File:** `src/carpix_images/services/storage.py:22-29`

**Issue:** `file_response()` delegates to `_validated_path()` which resolves the candidate path
and checks `is_relative_to(self._base)`. `save()` builds its path independently from the same
user-supplied `brand_key`, `model_key`, and `year` arguments but never calls `_validated_path()`
or performs any equivalent check. A caller passing `brand_key="../../../etc"` causes
`anyio.Path(self._base) / "../../../etc" / model_key / str(year)` to resolve outside `_base`,
and `mkdir(parents=True, exist_ok=True)` will create the directory tree and `write_bytes` will
overwrite an arbitrary file on the host filesystem.

**Proof (no async needed for path arithmetic):**
```python
from pathlib import Path
base = Path("/images").resolve()
candidate = base / "../../../etc" / "passwd" / "2020"
print(candidate.resolve())  # /etc/passwd/2020
```

**Fix:** Extract path construction into `_validated_path` (or a shared helper) and call it from
both methods. The simplest approach is to call `_validated_path` inside `save()` to obtain the
validated target, then `mkdir` on its parent:

```python
async def save(
    self, brand_key: str, model_key: str, year: int, data: bytes
) -> Path:
    target_file = self._validated_path(brand_key, model_key, year)  # raises on traversal
    target_dir = anyio.Path(target_file.parent)
    await target_dir.mkdir(parents=True, exist_ok=True)
    await anyio.Path(target_file).write_bytes(data)
    return target_file
```

---

### CR-02: `file_response()` Returns `FileResponse` Without Checking File Existence — Violates "Never a 500" Contract

**File:** `src/carpix_images/services/storage.py:31-35`

**Issue:** `file_response()` constructs and returns a `FileResponse` without verifying the file
exists. `FileResponse.__init__` is lazy: it accepts any path string without checking the
filesystem. The existence check happens inside `FileResponse.__call__` (the ASGI callable), which
calls `anyio.to_thread.run_sync(path.stat)`. If the file is absent, `FileNotFoundError` is raised
during response streaming; FastAPI does not catch this and returns HTTP 500.

`CLAUDE.md` states the core contract explicitly:

> _"never a 500, always a FileResponse or a clean 404"_

A missing-file case currently produces exactly the 500 this contract forbids.

**Fix:** Check existence synchronously before constructing `FileResponse`, and raise
`HTTPException(404)` when absent:

```python
from fastapi import HTTPException

def file_response(
    self, brand_key: str, model_key: str, year: int
) -> FileResponse:
    path = self._validated_path(brand_key, model_key, year)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(path=path, media_type="image/jpeg")
```

If callers prefer not to couple `StorageService` to `HTTPException`, an alternative is to raise a
domain-level `ImageNotFoundError` here and convert it to 404 in the router — either way the
`FileResponse` must never be returned for a path that does not exist.

---

## Warnings

### WR-01: `settings = Settings()` Eagerly Instantiated at Module Level

**File:** `src/carpix_images/config.py:18`

**Issue:** `Settings()` reads `DATABASE_URL` from the environment at import time (line 18).
Any module that imports `carpix_images.config` — directly or transitively — will raise
`pydantic_settings.ValidationError` if `DATABASE_URL` is absent from the process environment.
This has already required a workaround in `tests/conftest.py` (the `os.environ.setdefault` guard),
and will silently break if a future test file imports `config.py` before `conftest.py` has run or
if pytest collection order changes.

**Fix:** Use a lazy singleton pattern:

```python
from functools import lru_cache

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
```

Call `get_settings()` at usage sites instead of referencing the module-level `settings` object.
This is the pattern FastAPI's own docs recommend for dependency injection with settings.

---

### WR-02: Traversal Test Only Covers `..` Segments; `save()` Traversal Is Entirely Untested

**File:** `tests/unit/test_storage.py:40-43`

**Issue:** `test_traversal_attempt_raises_value_error` passes `".."` as both `brand_key` and
`model_key`. This confirms the `..` segment path, but does not test embedded-slash traversal
(`"foo/../../etc"`), which is a distinct attack vector that also escapes the base directory.
More critically, there is no test at all that verifies `save()` rejects a malicious key — because
`save()` currently has no traversal check (CR-01). Once CR-01 is fixed, the test suite needs
coverage of that fix.

**Fix:** Add the following tests:

```python
def test_traversal_with_embedded_slash_raises(self, tmp_path: Path) -> None:
    svc = StorageService(tmp_path)
    with pytest.raises(ValueError, match="traversal"):
        svc.file_response("foo/../../etc", "model", 2020)

async def test_save_traversal_attempt_raises(self, tmp_path: Path) -> None:
    svc = StorageService(tmp_path)
    with pytest.raises(ValueError, match="traversal"):
        await svc.save("..", "..", 2020, b"evil")
```

---

## Info

### IN-01: `file_response()` Test Does Not Assert `FileResponse` File Path or Media Type

**File:** `tests/unit/test_storage.py:33-38`

**Issue:** `test_valid_path_returns_file_response` asserts only `isinstance(resp, FileResponse)`.
It does not verify that `resp.path` points to the expected file or that `resp.media_type` is
`"image/jpeg"`. A regression that passes the wrong path or omits the media type would go
undetected.

**Fix:**
```python
def test_valid_path_returns_file_response(self, tmp_path: Path) -> None:
    svc = StorageService(tmp_path)
    (tmp_path / "toyota" / "camry" / "2020").mkdir(parents=True)
    (tmp_path / "toyota" / "camry" / "2020" / "image.jpg").write_bytes(b"DATA")
    resp = svc.file_response("toyota", "camry", 2020)
    assert isinstance(resp, FileResponse)
    assert resp.path == str(tmp_path / "toyota" / "camry" / "2020" / "image.jpg")
    assert resp.media_type == "image/jpeg"
```

---

### IN-02: `conftest.py` Uses Hardcoded Test Credentials in `DATABASE_URL`

**File:** `tests/conftest.py:4-6`

**Issue:** The fallback `DATABASE_URL` contains `user:pass@localhost:5432/testdb`. While
`setdefault` means this only activates when the variable is unset (so it never overrides a real
secret), embedding credentials in source code is a poor habit that scanners flag and that can
confuse future contributors into thinking these are real credentials.

**Fix:** Use a placeholder that is clearly not a credential, or document the value is a
test-only placeholder:

```python
# Dummy URL used only when no real DATABASE_URL is configured (e.g., unit-test runs
# that never touch Postgres). Integration tests must override this via environment.
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://testuser:testpass@localhost:5432/carpix_test",
)
```

Alternatively, use a `postgresql+asyncpg://` URL with clearly fake credentials
(`test:test@localhost`) so it is unambiguously a placeholder.

---

_Reviewed: 2026-05-23T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
