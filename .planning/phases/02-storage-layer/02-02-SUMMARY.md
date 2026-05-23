---
phase: 02-storage-layer
plan: 02
subsystem: storage
tags: [anyio, pathlib, fastapi, fileresponse, path-traversal-guard, pydantic-settings, tdd, green-implementation]

# Dependency graph
requires:
  - phase: 02-storage-layer
    plan: 01
    provides: StorageService stub with NotImplementedError bodies, 5 failing unit tests (RED baseline)
provides:
  - StorageService.save() fully implemented: async write via anyio.Path with automatic directory creation (STORE-01)
  - StorageService._validated_path(): path traversal guard using candidate.resolve().is_relative_to(self._base) (STORE-02)
  - StorageService.file_response(): synchronous method returning FileResponse(media_type='image/jpeg') (STORE-02)
  - Settings.images_dir: Path field defaulting to Path('/images'), overridable via IMAGES_DIR env var
affects: [Phase 05 ImageService (calls save() on cache miss, file_response() on cache hit)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "anyio.Path for async mkdir + write_bytes; return pathlib.Path for callers expecting pathlib"
    - "Path traversal guard: candidate.resolve().is_relative_to(self._base) — self._base pre-resolved in __init__"
    - "StorageService raises ValueError (not HTTPException) — router layer handles HTTP conversion"
    - "file_response() is synchronous def — only save() is async"
    - "str(year) enforced in path construction — pathlib / operator rejects int"
    - "ruff I001 import order: stdlib (pathlib) before third-party (pydantic, pydantic_settings)"

key-files:
  created: []
  modified:
    - src/carpix_images/services/storage.py
    - src/carpix_images/config.py

key-decisions:
  - "anyio.Path used for async I/O (mkdir, write_bytes); return type is pathlib.Path for FileResponse compatibility"
  - "self._base resolved once in __init__ via base_dir.resolve() — avoids re-resolving on every _validated_path call"
  - "Traversal guard raises ValueError with 'traversal' in message — not HTTPException; router layer converts to HTTP 400"
  - "images_dir uses pydantic Field(default=Path('/images')) pattern for Path type coercion from env var string"

patterns-established:
  - "Worktree file edits must use absolute paths rooted at worktree root (git rev-parse --show-toplevel), not main repo"
  - "PYTHONPATH=<worktree_root>/src required for test runs in worktree isolation"

requirements-completed:
  - STORE-01
  - STORE-02

# Metrics
duration: 8min
completed: 2026-05-23
---

# Phase 02 Plan 02: Storage Layer GREEN Implementation Summary

**StorageService fully implemented with async anyio.Path writes (STORE-01), candidate.resolve().is_relative_to() traversal guard (STORE-02), and Settings.images_dir: Path field — all 16 tests GREEN, ruff + mypy --strict clean**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-05-23T07:50:00Z
- **Completed:** 2026-05-23T07:58:43Z
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments

- Implemented `StorageService.save()` using `anyio.Path` for async `mkdir(parents=True, exist_ok=True)` and `write_bytes(data)`, returning `pathlib.Path` for caller compatibility; all 3 `TestStorageServiceSave` tests GREEN
- Implemented `StorageService._validated_path()` with `candidate.resolve().is_relative_to(self._base)` guard raising `ValueError` with "traversal" in message on escape attempt; `file_response()` delegates to guard then returns `FileResponse(media_type="image/jpeg")`; all 5 `TestStorageService` tests GREEN
- Extended `Settings` in `config.py` with `images_dir: Path = Field(default=Path("/images"))` using stdlib-before-third-party import order; full suite (16 tests), ruff, and mypy --strict all clean

## Task Commits

1. **Task 1: Implement StorageService.save() — STORE-01** - `556a8a3` (feat)
2. **Task 2: Implement StorageService._validated_path() + file_response() — STORE-02** - `dde3ef1` (feat)
3. **Task 3: Extend Settings with images_dir + full quality gate** - `84e2d80` (feat)

## Files Created/Modified

- `src/carpix_images/services/storage.py` - StorageService fully implemented: save() via anyio.Path, _validated_path() with traversal guard, file_response() returning FileResponse
- `src/carpix_images/config.py` - Added images_dir: Path = Field(default=Path('/images')) with stdlib import ordering

## Decisions Made

- **anyio.Path for async I/O, pathlib.Path as return type:** `anyio.Path` provides native async `mkdir` and `write_bytes` without blocking the event loop. The return value is cast to `pathlib.Path` so callers that check `isinstance(result, pathlib.Path)` or pass to `FileResponse(path=...)` work without issue.
- **self._base resolved once in __init__:** `base_dir.resolve()` in `__init__` handles symlinked Docker volumes at startup; subsequent calls to `_validated_path()` use the pre-resolved `self._base` without redundant `.resolve()` calls.
- **ValueError (not HTTPException) from StorageService:** Keeps StorageService decoupled from HTTP layer. The router (Phase 5) catches `ValueError` and converts to HTTP 400.
- **images_dir uses pydantic Field(default=...):** Allows env var override via `IMAGES_DIR=...` while defaulting to `/images`. Pydantic-settings handles string-to-Path coercion automatically.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Worktree path isolation — edits must target worktree root, not main repo**
- **Found during:** Task 1 (Implement StorageService.save())
- **Issue:** First Edit call targeted `/home/ccastro/Projects/carpix/src/...` (main repo path). The worktree has its own copy of the file at `<worktree_root>/src/...`. Tests passed (PYTHONPATH pointed to worktree) but `git status` showed nothing to commit because the main repo was edited, not the worktree.
- **Fix:** All subsequent Edit calls use worktree-relative paths verified against `git rev-parse --show-toplevel`.
- **Files modified:** `src/carpix_images/services/storage.py` (re-applied edit to worktree path)
- **Verification:** `git status --short` showed `M src/carpix_images/services/storage.py` after re-applying to worktree path
- **Committed in:** `556a8a3` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 3 - path isolation issue in worktree context)
**Impact on plan:** No functional impact. The implementation is identical; only the target path for the edit was corrected.

## Issues Encountered

- **Worktree path isolation:** Initial Edit used the main repo path `/home/ccastro/Projects/carpix/src/carpix_images/services/storage.py` instead of the worktree path. Tests using `PYTHONPATH=<worktree>/src` imported from the worktree copy (still stub), so the first test run appeared to pass against the wrong file. Detected via `git status` showing nothing to commit. Re-applied the edit to the correct worktree path and confirmed with `git status --short`.

## Known Stubs

None — all three `NotImplementedError` stubs from Plan 01 are now fully implemented.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes beyond the plan's documented threat model. T-02-01 and T-02-02 mitigations implemented as specified.

## Next Phase Readiness

- StorageService is production-ready: save() and file_response() fully implemented and tested
- Path traversal guard (STORE-02) verified against "..", ".." inputs
- Settings.images_dir available for Phase 5 ImageService to inject StorageService with correct base path
- No blockers for Phase 3 (DB models) or Phase 5 (ImageService)

## Self-Check: PASSED

- `src/carpix_images/services/storage.py` contains `await target_dir.mkdir(parents=True, exist_ok=True)` - VERIFIED
- `src/carpix_images/services/storage.py` contains `await target_file.write_bytes(data)` - VERIFIED
- `src/carpix_images/services/storage.py` contains `return Path(target_file)` - VERIFIED
- `src/carpix_images/services/storage.py` contains `is_relative_to(self._base)` - VERIFIED
- `src/carpix_images/services/storage.py` contains `raise ValueError` (not HTTPException) - VERIFIED
- `src/carpix_images/config.py` contains `images_dir: Path = Field(default=Path("/images"))` - VERIFIED
- Commit `556a8a3` (Task 1) - FOUND
- Commit `dde3ef1` (Task 2) - FOUND
- Commit `84e2d80` (Task 3) - FOUND
- 16 tests GREEN - VERIFIED
- ruff clean (src/ + tests/) - VERIFIED
- mypy --strict clean (9 source files) - VERIFIED

---
*Phase: 02-storage-layer*
*Completed: 2026-05-23*
