---
phase: "06"
slug: router-e2e-integration
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-29
---

# Phase 06 — Validation Strategy

> Per-phase validation contract reconstructed from 06-01-SUMMARY.md and 06-02-SUMMARY.md.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 (asyncio_mode=auto) |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `python -m pytest tests/unit/ -q` |
| **Full suite command** | `python -m pytest tests/ -q` |
| **Estimated runtime** | ~3 seconds (unit), ~30 seconds (full with testcontainers) |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/unit/ -q`
- **After every plan wave:** Run `python -m pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 06-01-01 | 01 | 1 | API-01, API-04 | T-06-06 | Stub raises NotImplementedError — RED intentional | unit | `pytest tests/unit/test_image_service.py -q` | ✅ | ✅ green |
| 06-01-02 | 01 | 1 | API-01, API-04 | — | N/A | unit | `pytest tests/unit/test_image_service.py -q` | ✅ | ✅ green |
| 06-01-03 | 01 | 1 | API-01, API-02, API-04 | T-06-06 | Router stub returns 500 at RED stage | integration | `pytest tests/integration/test_images_router.py -q` | ✅ | ✅ green |
| 06-02-01 | 02 | 2 | CACHE-01, CACHE-02, CACHE-03, CACHE-04, API-02 | T-06-02, T-06-04 | canonical_key normalization prevents path traversal | unit | `pytest tests/unit/test_image_service.py -q` | ✅ | ✅ green |
| 06-02-02 | 02 | 2 | API-01, API-04, DB-03 | T-06-05 | http_client.aclose() in lifespan finally prevents fd leak | integration | `pytest tests/integration/test_images_router.py -q` | ✅ | ✅ green |
| 06-02-03 | 02 | 2 | QUAL-01, QUAL-02 | — | Test isolation: TRUNCATE + rmtree before each module | integration | `pytest tests/ -q` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covered all phase requirements — no new setup needed.

Test files created during phase execution:
- `tests/unit/test_image_service.py` — 5 unit tests for ImageService (cache hit, miss, concurrent lock, self-healing, 404)
- `tests/integration/test_images_router.py` — 5 integration tests (X-Cache MISS, X-Cache HIT, 404, normalization, content-type)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| ruff + mypy --strict clean | QUAL-02 | Code quality gate, not a behavioral test; no automated test framework needed | Run `python -m ruff check src/ tests/` and `python -m mypy --strict src/` — both must exit 0 |

---

## Requirements Coverage

| Requirement | Description | Test File | Test Name | Status |
|-------------|-------------|-----------|-----------|--------|
| API-01 | GET /v1/images/{brand}/{model}/{year} returns FileResponse + image/jpeg | `tests/integration/test_images_router.py` | `test_cache_miss_returns_jpeg_with_x_cache_miss_header`, `test_cache_hit_returns_jpeg_with_x_cache_hit_header`, `test_content_type_is_image_jpeg` | ✅ COVERED |
| API-02 | HTTP 404 with detail message when Wikimedia fails | `tests/unit/test_image_service.py`, `tests/integration/test_images_router.py` | `test_raises_http_exception_404_when_no_image_found`, `test_no_wikimedia_result_returns_404` | ✅ COVERED |
| API-04 | X-Cache: HIT or MISS header | `tests/integration/test_images_router.py` | `test_cache_miss_returns_jpeg_with_x_cache_miss_header`, `test_cache_hit_returns_jpeg_with_x_cache_hit_header` | ✅ COVERED |
| QUAL-01 | Full unit + integration coverage; respx mocks; real Postgres via testcontainers | `tests/unit/test_image_service.py`, `tests/integration/test_images_router.py` | All 10 phase tests | ✅ COVERED |
| QUAL-02 | ruff + mypy --strict clean before every commit | — | Manual gate | ⚙️ MANUAL |

---

## Validation Sign-Off

- [x] All tasks have automated verify or explicit manual-only justification
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 not needed — existing infrastructure covered all requirements
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-05-29

---

## Validation Audit 2026-05-29

| Metric | Count |
|--------|-------|
| Requirements audited | 5 |
| COVERED | 4 |
| MANUAL | 1 |
| MISSING | 0 |
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
