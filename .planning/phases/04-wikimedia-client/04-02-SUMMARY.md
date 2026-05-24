---
phase: 04-wikimedia-client
plan: "02"
subsystem: wikimedia-client
tags: [tdd, green, wikimedia, httpx, respx, mypy-strict]
dependency_graph:
  requires: [04-01]
  provides: [WikimediaClient full implementation, GREEN test baseline for WIKI-01/WIKI-02/WIKI-03]
  affects: [src/carpix_images/services/wikimedia.py]
tech_stack:
  added: []
  patterns: [TDD GREEN, dependency injection, typed Any annotations for mypy strict]
key_files:
  created: []
  modified:
    - src/carpix_images/services/wikimedia.py
decisions:
  - dict[str, Any] and list[Any] used for all JSON-typed local variables to satisfy mypy --strict without type: ignore suppressions
  - lambda p p.get("index", 999) works without type: ignore after annotating candidates as list[Any]
  - No docstrings added per plan directive; implementation is self-explanatory
metrics:
  duration: 2 minutes
  completed: 2026-05-24
  tasks_completed: 2
  files_changed: 1
---

# Phase 04 Plan 02: WikimediaClient TDD GREEN Implementation Summary

**One-liner:** WikimediaClient full implementation — find_jpeg_url with two-query fallback chain and JPEG mime filter, ruff + mypy --strict clean, all 6 RED tests now GREEN.

## What Was Built

- **src/carpix_images/services/wikimedia.py**: Replaced NotImplementedError stubs with the full implementation. `find_jpeg_url` calls `_search_first_jpeg` with the primary query `f"{year} {brand} {model}"`, then falls back to `f"{brand} {model}"` if primary returns None. `_search_first_jpeg` issues a combined `generator=search` + `prop=imageinfo` Wikimedia API call, sorts results by `index` field, filters for `mime == "image/jpeg"`, and returns `str(info["thumburl"])` for the first match. Both methods are fully typed with `dict[str, Any]` and `list[Any]` annotations to satisfy mypy --strict.

## Tasks

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Implement WikimediaClient (GREEN) | 53b6b42 | src/carpix_images/services/wikimedia.py |
| 2 | ruff + mypy --strict clean and full unit suite gate | (verification only, no file changes) | — |

## Test Results

```
collected 6 items
PASSED test_find_jpeg_url_returns_thumburl_exactly
PASSED test_skips_svg_and_returns_none
PASSED test_skips_png_and_returns_none
PASSED test_selects_jpeg_from_mixed_types
PASSED test_fallback_query_called_when_primary_returns_no_jpeg
PASSED test_returns_none_when_both_queries_yield_no_jpeg
6 passed, 0 failed, 0 errors
```

Full unit suite: 22 passed (6 wikimedia + 16 pre-existing tests). No regression.

## Phase 4 Success Criteria

- SC1 (WIKI-01): test_find_jpeg_url_returns_thumburl_exactly PASSED — thumburl returned exactly as received
- SC2 (WIKI-02): test_skips_svg_and_returns_none, test_skips_png_and_returns_none, test_selects_jpeg_from_mixed_types all PASSED
- SC3 (WIKI-03): test_fallback_query_called_when_primary_returns_no_jpeg PASSED + call_count == 2 asserted
- SC4 (WIKI-03 tail): test_returns_none_when_both_queries_yield_no_jpeg PASSED + no exception raised

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed unused type: ignore[union-attr] comment**
- **Found during:** Task 1 mypy --strict run
- **Issue:** mypy --strict flagged `# type: ignore[union-attr]` on the sorted() lambda as an unused ignore comment (error: Unused "type: ignore" comment [unused-ignore]) — the annotation `candidates: list[Any]` already resolved the type issue without needing the ignore
- **Fix:** Removed the `# type: ignore[union-attr]` comment from the sorted() call
- **Files modified:** src/carpix_images/services/wikimedia.py
- **Commit:** 53b6b42 (included in same commit)

No architectural deviations. Plan executed exactly as designed.

## TDD Gate Compliance

- RED gate commit: `test(04-01): add 6 failing unit tests for WikimediaClient (RED baseline)` (31c032d) — PRESENT (prior wave)
- GREEN gate commit: `feat(04-02): implement WikimediaClient GREEN — all 6 tests passing` (53b6b42) — PRESENT
- REFACTOR gate commit: Not needed — implementation is clean on first pass

## Known Stubs

None — both previously-stubbed methods are fully implemented and tested.

## Threat Flags

No new security surface introduced. Implementation uses `httpx params=` dict for URL encoding (T-04-02-T mitigated), calls `response.raise_for_status()` before parsing (T-04-02-D propagation path wired), and returns `thumburl` as-is without modification (SSRF note delegated to Phase 5 per T-04-02-E).

## Self-Check: PASSED

- src/carpix_images/services/wikimedia.py: FOUND
- Commit 53b6b42: FOUND
- 6 tests GREEN: CONFIRMED (6 passed, 0 failed, 0 errors)
- ruff check: PASSED (exit code 0)
- mypy --strict: PASSED ("Success: no issues found in 1 source file")
- Full unit suite (22 tests): PASSED
