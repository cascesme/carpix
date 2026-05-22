# Phase 1: Foundation - Context

**Gathered:** 2026-05-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Stand up the runnable FastAPI app skeleton: build tooling (uv), package layout (src/carpix_images/), pydantic-settings config, normalization logic, and health endpoints. Output is a `uvicorn main:app`-startable service with `/health` and `/docs` discoverable.

</domain>

<decisions>
## Implementation Decisions

### Build Tool
- **D-01:** Use **uv** as package manager and build tool. `pyproject.toml` uses uv conventions (`[tool.uv]` if needed, `uv.lock` lockfile). Multi-stage Dockerfile uses `uv pip install` or `uv sync`. No hatchling or plain pip.

### Package Layout
- **D-02:** **src-layout** — source code lives at `src/carpix_images/`. Package name is `carpix_images`. Mirrors parent project (`auto-insight-claw`) convention. `pythonpath = ["src"]` in pytest config, `mypy_path = "src"` in mypy config.

### Health Response Schema
- **D-03:** `GET /health` always returns **HTTP 200** — process liveness is unconditional. DB probe result appears in the body only.
- **D-04:** Response body when DB is reachable: `{"status": "ok", "db": "ok"}`. When DB is unreachable: `{"status": "ok", "db": "error"}`. Flat strings, no nesting.

### Config Layer
- **D-05:** Use **pydantic-settings** (`BaseSettings`). Mirrors parent project. Validates env vars at startup — missing required vars crash early with a clear error.
- **D-06:** Phase 1 configures **`DATABASE_URL` only**. `IMAGES_DIR` and all other settings added in their respective phases. No forward-declaration of unused config.

### Claude's Discretion
- App factory pattern: use `create_app() -> FastAPI` function (mirrors parent project's `main.py` pattern).
- Lifespan: use FastAPI `@asynccontextmanager` lifespan (modern pattern, not deprecated `@app.on_event`). DB pool wiring happens in Phase 3 — Phase 1 lifespan can be a no-op or minimal.
- Internal module structure within `src/carpix_images/`: Claude selects (e.g., `config.py`, `main.py`, `routers/health.py`, `domain/normalize.py`).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Normalization Logic (locked — NORM-01)
- `/home/ccastro/Projects/auto-insight-claw/src/auto_insight_claw/domain/vehicle_identity.py` — `canonical_key` function at line 15. Implementation MUST match: `re.sub(r"[^a-z0-9]", "", value.lower())`. This is the exact function from the parent project.

### Parent Project Patterns (reference, not copy)
- `/home/ccastro/Projects/auto-insight-claw/src/auto_insight_claw/main.py` — `create_app()` factory pattern, middleware wiring, FastAPI constructor args.
- `/home/ccastro/Projects/auto-insight-claw/src/auto_insight_claw/config.py` — `pydantic-settings` `BaseSettings` pattern with `.env` file support.
- `/home/ccastro/Projects/auto-insight-claw/pyproject.toml` — `mypy --strict`, `ruff` config, `pytest-asyncio` in auto mode, `testcontainers[postgres]` in dev deps. Use as reference for tool config.

### Requirements
- `.planning/REQUIREMENTS.md` — NORM-01, API-03, API-05 are the Phase 1 requirements. Full acceptance criteria in `.planning/ROADMAP.md` Phase 1 section.
- `.planning/ROADMAP.md` — Phase 1 success criteria (4 items).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `canonical_key` from parent project: copy function verbatim into `src/carpix_images/domain/normalize.py` — do not import from parent, no runtime dependency on auto-insight-claw.

### Established Patterns
- **App factory:** Parent uses `create_app() -> FastAPI` called at module level (`app = create_app()` in main or via uvicorn entrypoint). Follow same pattern.
- **pydantic-settings:** Parent instantiates `settings = Settings()` at module level. Same pattern here.
- **mypy overrides:** Parent has `[[tool.mypy.overrides]]` for asyncpg, alembic, testcontainers — reuse same ignore patterns.
- **ruff:** `select = ["E", "F", "I", "UP"]`, `target-version = "py312"`, `line-length = 88` — match parent.
- **pytest-asyncio:** `asyncio_mode = "auto"` — match parent.

### Integration Points
- Phase 1 health endpoint is a standalone router with no downstream dependencies (no DB pool yet in Phase 1 — health makes a raw `asyncpg.connect()` probe on each call, or holds a minimal test connection, then reports result without failing the request).

</code_context>

<specifics>
## Specific Ideas

- Health endpoint DB probe: `SELECT 1` via a short-lived asyncpg connection (not the full pool — pool is wired in Phase 3). On connection failure, catch the exception, set `db = "error"`, return 200 regardless.
- Normalization: `clean_display` from parent (lowercase + collapse hyphens/whitespace) is NOT needed in Phase 1 — only `canonical_key` is required for NORM-01. Do not add `clean_display` unless a later phase needs it.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 1-Foundation*
*Context gathered: 2026-05-22*
