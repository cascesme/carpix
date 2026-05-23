---
phase: 2
slug: storage-layer
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-22
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 + pytest-asyncio 1.3.0 |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` (`asyncio_mode = "auto"`) |
| **Quick run command** | `python3 -m pytest tests/unit/test_storage.py -x -q` |
| **Full suite command** | `python3 -m pytest tests/ -x -q && python3 -m ruff check src/ tests/ && python3 -m mypy src/` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python3 -m pytest tests/unit/test_storage.py -x -q`
- **After every plan wave:** Run `python3 -m pytest tests/ -x -q && python3 -m ruff check src/ tests/ && python3 -m mypy src/`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 0 | STORE-01, STORE-02 | T-02-01 | path traversal raises ValueError | unit | `python3 -m pytest tests/unit/test_storage.py -x -q` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | STORE-01 | — | save() writes at correct path, creates dirs | unit | `python3 -m pytest tests/unit/test_storage.py::TestStorageServiceSave -x -q` | ❌ W0 | ⬜ pending |
| 02-01-03 | 01 | 1 | STORE-02 | T-02-01 | valid path returns FileResponse | unit | `python3 -m pytest tests/unit/test_storage.py::TestStorageServiceFileResponse -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/test_storage.py` — failing stubs for STORE-01 and STORE-02 (5 test cases)
- [ ] `src/carpix_images/services/__init__.py` — empty package init (required for import)
- [ ] `src/carpix_images/services/storage.py` — `StorageService` stub that fails tests

*Existing pytest + pytest-asyncio infrastructure covers all phase requirements — no new framework install.*

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
