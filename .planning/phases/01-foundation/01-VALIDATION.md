---
phase: 1
slug: foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-22
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` — created in Wave 0 |
| **Quick run command** | `pytest tests/unit/ -x` |
| **Full suite command** | `pytest tests/ -x && ruff check src/ tests/ && mypy src/` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/unit/ -x`
- **After every plan wave:** Run `pytest tests/ -x && ruff check src/ tests/ && mypy src/`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 0 | — | — | N/A | setup | `command -v uv \|\| curl -LsSf https://astral.sh/uv/install.sh \| sh` | ✅ | ⬜ pending |
| 1-01-02 | 01 | 0 | NORM-01, API-03, API-05 | — | N/A | setup | `pytest tests/unit/ -x` (after stubs created) | ❌ W0 | ⬜ pending |
| 1-02-01 | 02 | 1 | NORM-01 | — | N/A | unit | `pytest tests/unit/test_normalize.py -x` | ❌ W0 | ⬜ pending |
| 1-02-02 | 02 | 1 | API-03, API-05 | — | Health catches all exceptions; no stack traces returned | unit | `pytest tests/unit/test_health.py -x` | ❌ W0 | ⬜ pending |
| 1-02-03 | 02 | 1 | API-03 | — | N/A | unit | `pytest tests/unit/test_health.py::test_docs_accessible -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/__init__.py` — empty, required for pytest collection
- [ ] `tests/conftest.py` — `os.environ.setdefault("DATABASE_URL", ...)` before any carpix_images import
- [ ] `tests/unit/__init__.py` — empty
- [ ] `tests/unit/test_normalize.py` — stubs for NORM-01 (parametrized)
- [ ] `tests/unit/test_health.py` — stubs for API-03, API-05 (mocked asyncpg)
- [ ] `tests/integration/__init__.py` — placeholder for Phase 3+
- [ ] `pyproject.toml` — with `[tool.pytest.ini_options]`, `[tool.mypy]`, `[tool.ruff]`

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
