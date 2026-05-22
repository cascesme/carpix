# Phase 1: Foundation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-22
**Phase:** 1-Foundation
**Areas discussed:** Build tool, Package layout, Health response schema, Config layer

---

## Build Tool

| Option | Description | Selected |
|--------|-------------|----------|
| uv | uv-managed pyproject.toml + uv.lock. Fast installs, reproducible lockfile. CLAUDE.md sources cite uv+FastAPI+Docker guide. | ✓ |
| pip + hatchling | Mirrors parent project (`auto-insight-claw`). Uses hatchling build backend with src-layout. Multi-stage Dockerfile uses plain pip install. | |
| pip-only | pyproject.toml with minimal metadata only, plain `pip install -r requirements.txt`. Simplest, no build backend. | |

**User's choice:** uv
**Notes:** None — clear preference for modern tooling.

---

## Package Layout

| Option | Description | Selected |
|--------|-------------|----------|
| src/carpix_images/ | src-layout matching the parent project. Package name `carpix_images` mirrors the service name. | ✓ |
| app/ (flat) | Top-level `app/` directory. Common pattern for pure services. Simpler imports, diverges from parent convention. | |
| Top-level modules | main.py, routers/, services/ etc. at repo root. No package wrapper. | |

**User's choice:** `src/carpix_images/` with src-layout
**Notes:** None — mirrors parent project pattern.

---

## Health Response Schema

| Option | Description | Selected |
|--------|-------------|----------|
| `{"status": "ok", "db": "ok"}` | Flat strings. Simple. Process always "ok"; db field changes on failure. | ✓ |
| `{"healthy": true, "database": {"reachable": true}}` | Nested object for DB probe, booleans instead of strings. More extensible. | |
| You decide | Claude picks simplest valid schema satisfying API-03 and API-05. | |

**Sub-question — HTTP status on DB failure:**

| Option | Description | Selected |
|--------|-------------|----------|
| 200 always | Process liveness is separate from DB health. ROADMAP explicitly requires 200 even when DB unreachable. | ✓ |
| 503 when DB down | Signals degraded state to load balancers. Conflicts with stated requirement. | |

**User's choice:** `{"status": "ok", "db": "ok"}` / `{"status": "ok", "db": "error"}` — always HTTP 200.
**Notes:** Flat schema, process liveness unconditional.

---

## Config Layer

| Option | Description | Selected |
|--------|-------------|----------|
| pydantic-settings | Mirrors parent project. Reads from .env and env vars. Validated at startup — missing required vars crash early. | ✓ |
| bare os.environ | No extra dependency. Values are strings only, no validation. Loses startup-crash guarantee. | |

**Sub-question — which env vars in Phase 1:**

| Option | Description | Selected |
|--------|-------------|----------|
| DATABASE_URL only | Only what Phase 1 uses: DB connection string for health probe. Others added in their phases. | ✓ |
| DATABASE_URL + IMAGES_DIR | Pre-wire IMAGES_DIR to avoid a two-file edit in Phase 2. | |
| DATABASE_URL + LOG_LEVEL | Add LOG_LEVEL as dev/prod convenience even without structured logging in Phase 1. | |

**User's choice:** pydantic-settings + DATABASE_URL only.
**Notes:** Incremental config — no forward-declaration of unused settings.

---

## Claude's Discretion

- App factory pattern: `create_app() -> FastAPI` (mirrors parent)
- Lifespan: FastAPI `@asynccontextmanager` lifespan (modern, not deprecated `@app.on_event`)
- Internal module structure within `src/carpix_images/`

## Deferred Ideas

None — discussion stayed within phase scope.
