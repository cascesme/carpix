---
phase: 07-containerization
plan: "01"
subsystem: infrastructure
tags: [docker, containerization, security, multi-stage-build]
dependency_graph:
  requires: []
  provides: [carpix-images-docker-image]
  affects: [07-02-docker-compose]
tech_stack:
  added: [multi-stage Docker build, uv sync --no-dev]
  patterns: [non-root appuser, venv-only runtime stage, COPY --from=builder]
key_files:
  created:
    - Dockerfile
    - .dockerignore
  modified: []
decisions:
  - "Used `pip install uv` in builder stage (uv not pre-installed in python:3.12-slim; builder stage is discarded so pip root warning is acceptable)"
  - "ENV PYTHONPATH=/app/src set to support src-layout package import without installing editable package in runtime stage"
  - "/images directory created with chown before USER appuser switch — must be done as root"
metrics:
  duration: "1 minute"
  completed: "2026-05-24T14:22:00Z"
  tasks_completed: 2
  files_created: 2
  files_modified: 0
---

# Phase 07 Plan 01: Dockerfile + .dockerignore Summary

**One-liner:** Multi-stage Dockerfile with uv builder and non-root appuser runtime; production image excludes all dev dependencies.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Write .dockerignore | b73c2ca | .dockerignore |
| 2 | Write multi-stage Dockerfile | ff54a55 | Dockerfile |

## What Was Built

### .dockerignore
Excludes non-production content from the Docker build context:
- `.venv/`, `.git/`, `.planning/`, `tests/` — build artifacts and dev-only directories
- `.env`, `.env.*` — secrets excluded; DATABASE_URL injected at runtime
- Python bytecode caches (`__pycache__/`, `*.pyc`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`)

Kept in build context (required by builder): `src/`, `alembic/`, `alembic.ini`, `pyproject.toml`, `uv.lock`

### Dockerfile (two-stage)

**Builder stage** (`python:3.12-slim`):
1. Installs `uv` via `pip install --no-cache-dir uv`
2. Copies `pyproject.toml` + `uv.lock` for layer cache
3. Runs `uv sync --no-dev --frozen` — installs only production deps into `.venv`
4. Copies `src/`, `alembic/`, `alembic.ini`

**Runtime stage** (`python:3.12-slim`):
1. Creates `appuser` group and user (non-root, T-07-01 mitigated)
2. `COPY --from=builder` — venv, src, alembic, alembic.ini (no build tooling)
3. Creates `/images` directory, `chown appuser:appuser /images`
4. `ENV PATH="/app/.venv/bin:$PATH"` and `ENV PYTHONPATH="/app/src"`
5. `USER appuser`
6. `CMD ["uvicorn", "carpix_images.main:app", "--host", "0.0.0.0", "--port", "8000"]`

## Verification Results

| Check | Command | Result |
|-------|---------|--------|
| Build exits 0 | `docker build -t carpix-images:test .` | PASS |
| Runs as appuser | `docker run --rm carpix-images:test whoami` | `appuser` |
| /images owned by appuser | `docker run --rm ... ls -la / \| grep images` | `drwxr-xr-x 2 appuser appuser` |
| Inspect user | `docker inspect --format='{{.Config.User}}'` | `appuser` |
| Import carpix_images | `/app/.venv/bin/python -c "import carpix_images"` | PASS |
| No pytest in image | `pip list \| grep -i pytest` | empty (PASS) |
| No ruff in image | `pip list \| grep -i ruff` | empty (PASS) |
| No mypy in image | `pip list \| grep -i mypy` | empty (PASS) |
| Two FROM stages | `grep -c "^FROM " Dockerfile` | `2` |

## Deviations from Plan

None — plan executed exactly as written.

## Threat Mitigations Applied

| Threat ID | Mitigation |
|-----------|-----------|
| T-07-01 (Elevation of Privilege) | `USER appuser` in runtime stage; UID has no sudo, no capabilities |
| T-07-04 (Info Disclosure: .env) | `.dockerignore` excludes `.env` and `.env.*` |

Threats T-07-02, T-07-03, T-07-SC accepted per plan disposition.

## Known Stubs

None.

## Threat Flags

None — no new network endpoints, auth paths, file access patterns, or schema changes introduced.

## Self-Check: PASSED

- `Dockerfile` exists: FOUND
- `.dockerignore` exists: FOUND
- Commit `b73c2ca` exists: FOUND (chore(07-01): add .dockerignore)
- Commit `ff54a55` exists: FOUND (feat(07-01): add multi-stage Dockerfile)
- `docker build .` exits 0: VERIFIED
- `whoami` returns `appuser`: VERIFIED
- `/images` owned by `appuser`: VERIFIED
- No dev deps in image: VERIFIED
