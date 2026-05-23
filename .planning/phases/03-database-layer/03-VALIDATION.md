---
phase: 3
slug: database-layer
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-23
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio + testcontainers |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `uv run pytest tests/unit/ -q` |
| **Full suite command** | `uv run pytest -q` |
| **Estimated runtime** | ~30 seconds (unit) / ~90 seconds (integration with container) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/unit/ -q`
- **After every plan wave:** Run `uv run pytest -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 90 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 3-01-01 | 01 | 0 | DB-01 | — | N/A | unit | `uv run pytest tests/ -q -k "migration"` | ❌ W0 | ⬜ pending |
| 3-01-02 | 01 | 1 | DB-02 | — | N/A | integration | `uv run pytest tests/ -q -k "cache_repository"` | ❌ W0 | ⬜ pending |
| 3-01-03 | 01 | 1 | DB-03 | — | N/A | integration | `uv run pytest tests/ -q -k "pool"` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/integration/test_cache_repository.py` — stubs for DB-02 (find/insert)
- [ ] `tests/integration/conftest.py` — testcontainers Postgres fixture
- [ ] `tests/unit/test_migration.py` — Alembic migration smoke test stub

*Existing test infrastructure may need `sqlalchemy`, `alembic`, `testcontainers` added to dev deps.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Connection pool closes cleanly on shutdown | DB-03 | Lifespan teardown requires running server | `uvicorn app.main:app`, Ctrl+C, check logs for "Engine disposed" |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 90s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
