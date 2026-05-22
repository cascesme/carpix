<!-- GSD:project-start source:PROJECT.md -->
## Project

**Vehicle Image Cache Microservice (carpix-images)**

A standalone FastAPI microservice that serves car images by brand, model, and year. On the first request for a given vehicle, it fetches a CC-licensed image from Wikimedia Commons, saves an 800px thumbnail locally, and returns it — all subsequent requests for that vehicle are served directly from the filesystem cache. Deployed as a sibling Docker container alongside the parent carpix application.

**Core Value:** Any vehicle query is answered with an image — cache hit or Wikimedia fetch — never a 500, always a FileResponse or a clean 404.

### Constraints

- **Tech stack**: FastAPI (Python, async) — mirrors parent project
- **Storage**: Local filesystem at `/images/{brand_key}/{model_key}/{year}/image.jpg`
- **Database**: PostgreSQL — same engine as parent project
- **Containerization**: Docker + docker-compose with `/images` volume for persistence
- **Image width**: 800px via Wikimedia CDN thumbnail pattern only (no PIL/Pillow resize)
- **Error handling**: Extraction failures always 404, never 500
- **Development**: SOLID principles, TDD (tests first), ruff + mypy clean before commit
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack

## Recommended Stack
### Core
### Database
- asyncpg is a pure-async driver with no thread-pool adapter layer; it does not block the event
- SQLAlchemy 2.0 has first-class asyncpg support via `create_async_engine("postgresql+asyncpg://...")`
- For a cache microservice the bottleneck is the Wikimedia HTTP fetch, not the DB; asyncpg's
- asyncpg 0.31.0 is the current stable release; well-maintained, widely deployed
### HTTP Client
- Native async/await; no thread-pool wrapper unlike requests
- Used by FastAPI's own `TestClient` internally, so the testing integration is seamless
- Wikimedia requires a User-Agent header on API calls; httpx's default headers are clean to
### Testing
- respx integrates directly with httpx transport (no patching, no leakage between tests)
- URL pattern matching (`respx.get("https://commons.wikimedia.org/...").respond(...)`) is
- async-native by design, not an afterthought
### Tooling
## What NOT to Use
## Key Trade-offs
## Installation
# pyproject.toml
## Sources
- FastAPI official docs: https://fastapi.tiangolo.com/advanced/custom-response/ (FileResponse)
- SQLAlchemy asyncio docs: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
- asyncpg PyPI: https://pypi.org/project/asyncpg/
- Alembic async cookbook: https://alembic.sqlalchemy.org/en/latest/cookbook.html
- httpx official docs: https://www.python-httpx.org/advanced/timeouts/
- respx GitHub: https://github.com/lundberg/respx
- pytest-asyncio docs: https://pytest-asyncio.readthedocs.io/
- testcontainers-python docs: https://testcontainers-python.readthedocs.io/
- testcontainers + FastAPI + asyncpg: https://lealre.github.io/fastapi-testcontainer-asyncpg/
- ruff configuration: https://docs.astral.sh/ruff/configuration/
- uv + FastAPI + Docker: https://docs.astral.sh/uv/guides/integration/fastapi/
- asyncpg vs psycopg3 comparison: https://fernandoarteaga.dev/blog/psycopg-vs-asyncpg/
- Modern Python tooling 2026: https://softaims.com/blog/modern-python-tooling-uv-ruff-mypy-2026
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
