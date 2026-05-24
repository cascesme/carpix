---
phase: 04-wikimedia-client
plan: "01"
subsystem: wikimedia-client
tags: [tdd, red-baseline, wikimedia, httpx, respx]
dependency_graph:
  requires: [03-database-layer]
  provides: [WikimediaClient stub, RED test baseline for WIKI-01/WIKI-02/WIKI-03]
  affects: [src/carpix_images/services/wikimedia.py, tests/unit/test_wikimedia.py]
tech_stack:
  added: [httpx moved to prod deps]
  patterns: [TDD RED baseline, dependency injection, respx transport mocking]
key_files:
  created:
    - src/carpix_images/services/wikimedia.py
    - tests/unit/test_wikimedia.py
  modified:
    - pyproject.toml
decisions:
  - httpx moved to [project].dependencies so WikimediaClient is importable in production without dev extras
  - WikimediaClient stub raises NotImplementedError on both public methods to guarantee RED baseline
  - respx_mock fixture used (not @respx.mock decorator) per pitfall 3 in research — avoids event loop conflicts with pytest-asyncio asyncio_mode=auto
  - assert_all_called=False mark applied to SVG and PNG skip tests to avoid respx teardown assertion when fallback call is not needed
  - side_effect list used for sequential responses in fallback and no-result tests
metrics:
  duration: 3 minutes
  completed: 2026-05-24
  tasks_completed: 2
  files_changed: 3
---

# Phase 04 Plan 01: WikimediaClient TDD RED Baseline Summary

**One-liner:** WikimediaClient stub with NotImplementedError and 6 respx-mocked RED unit tests locking in WIKI-01/WIKI-02/WIKI-03 contract.

## What Was Built

- **pyproject.toml**: Moved `httpx>=0.28.1` from `[project.optional-dependencies].dev` to `[project].dependencies`. Production code (`WikimediaClient`) requires httpx at runtime.
- **src/carpix_images/services/wikimedia.py**: WikimediaClient stub following the CacheRepository DI pattern. Module-level constants `_COMMONS_API` and `_USER_AGENT`. Two async methods (`find_jpeg_url`, `_search_first_jpeg`) each raise `NotImplementedError`. Ruff and mypy --strict pass on stub.
- **tests/unit/test_wikimedia.py**: 6 unit tests — all FAILING with `NotImplementedError` against the stub (RED baseline). Tests cover WIKI-01, WIKI-02 (a/b/c), and WIKI-03 (a/b). Uses `respx_mock` fixture for transport-level HTTP interception. Ruff clean.

## Tasks

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Move httpx to prod deps and create WikimediaClient stub | b9dfeb5 | pyproject.toml, src/carpix_images/services/wikimedia.py |
| 2 | Write 6 failing unit tests (RED baseline) | 31c032d | tests/unit/test_wikimedia.py |

## Test Results

```
collected 6 items
FAILED test_find_jpeg_url_returns_thumburl_exactly     (NotImplementedError)
FAILED test_skips_svg_and_returns_none                 (NotImplementedError)
FAILED test_skips_png_and_returns_none                 (NotImplementedError)
FAILED test_selects_jpeg_from_mixed_types              (NotImplementedError)
FAILED test_fallback_query_called_when_primary_returns_no_jpeg  (NotImplementedError)
FAILED test_returns_none_when_both_queries_yield_no_jpeg        (NotImplementedError)
```

All 6 FAILED (expected). 0 PASSED. 0 ERROR. RED baseline locked.

Existing unit tests: 5/5 PASSED (no regression in test_storage.py).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed 3 line-length ruff E501 violations in test file**
- **Found during:** Task 2 ruff check
- **Issue:** Inline imageinfo list dicts exceeded 88-char line limit in SVG/PNG test cases
- **Fix:** Wrapped inline dict onto two lines with explicit list brackets
- **Files modified:** tests/unit/test_wikimedia.py
- **Commit:** 31c032d (included in same commit)

No architectural deviations. Plan executed exactly as designed.

## TDD Gate Compliance

- RED gate commit: `test(04-01): add 6 failing unit tests for WikimediaClient (RED baseline)` (31c032d) — PRESENT
- GREEN gate commit: Not applicable — Wave 2 (Plan 02) implements the client
- REFACTOR gate commit: Not applicable — same as above

## Known Stubs

| Stub | File | Line | Reason |
|------|------|------|--------|
| `find_jpeg_url` raises NotImplementedError | src/carpix_images/services/wikimedia.py | 16 | Intentional TDD RED stub — Wave 2 (04-02) implements |
| `_search_first_jpeg` raises NotImplementedError | src/carpix_images/services/wikimedia.py | 19 | Intentional TDD RED stub — Wave 2 (04-02) implements |

## Threat Flags

No new security surface introduced. Both files are test infrastructure and a stub implementation. No new network endpoints, auth paths, or schema changes.

## Self-Check: PASSED

- src/carpix_images/services/wikimedia.py: FOUND
- tests/unit/test_wikimedia.py: FOUND
- pyproject.toml (httpx in prod deps): FOUND (line 15, absent from dev)
- Commit b9dfeb5: FOUND
- Commit 31c032d: FOUND
- 6 tests RED: CONFIRMED (0 PASSED, 0 ERROR)
