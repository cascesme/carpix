# Phase 4: Wikimedia Client - Research

**Researched:** 2026-05-24
**Domain:** Wikimedia Commons MediaWiki API, httpx async HTTP client, respx transport mocking
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| WIKI-01 | Fetch `thumburl` from Wikimedia imageinfo API and use directly — no manual URL construction | Confirmed: `thumburl` field is present in every successful imageinfo response. Wikimedia rounds iiurlwidth to a CDN-standard size (request 800 → URL contains 960px); the `thumburl` field is the authoritative download URL. |
| WIKI-02 | Only JPEG results selected (`mime: image/jpeg`); SVG, TIFF, PNG skipped | Confirmed: `mime` field is present in every imageinfo response. Verified via live API calls that SVG (`image/svg+xml`), PNG (`image/png`), and JPEG (`image/jpeg`) all appear in real search results. Filter on `mime == "image/jpeg"`. |
| WIKI-03 | Fallback query: if `{year} {brand} {model}` yields no JPEG candidate, retry with `{brand} {model}` before returning None | The fallback is a straightforward second API call with the shorter query string. No special API support needed — just call the same method with the simplified query. |
</phase_requirements>

---

## Summary

Phase 4 builds `WikimediaClient` — a single class that resolves a vehicle query to a downloadable 800px JPEG URL and its file bytes. The client calls the Wikimedia Commons MediaWiki API across two logical steps (searchable as one combined API call), filters for JPEG candidates by `mime` field, and retries with a shorter query on miss.

The Wikimedia Commons API supports combining `generator=search` with `prop=imageinfo` in a single HTTP request, which collapses the "search API → imageinfo API" chain into one network call. This is an implementation efficiency — the requirement's "3-step" language refers to the logical flow (search → resolve → download), not a mandate for three separate HTTP requests. The combined call is confirmed working via live API tests in this session.

All dependencies for this phase (`httpx`, `respx`) are already declared in `pyproject.toml`. No new packages need to be added. The `respx` `respx_mock` pytest fixture intercepts all `httpx.AsyncClient` calls globally via transport-layer patching of `httpx._client.AsyncClient._transport_for_url` — no dependency injection of the client is required for testability, though injecting the client is still the cleanest design.

**Primary recommendation:** Implement `WikimediaClient` in `src/carpix_images/services/wikimedia.py` with an injected `httpx.AsyncClient`. Use a single combined `generator=search` + `prop=imageinfo` API call, filter `imageinfo[0]["mime"] == "image/jpeg"`, and expose a `find_jpeg_url(brand: str, model: str, year: int) -> str | None` method that internally retries with the shorter query.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Wikimedia search + imageinfo API calls | API / Backend (services) | — | Outbound HTTP from service tier; not browser/CDN concern |
| JPEG mime filtering | API / Backend (services) | — | Pure Python logic inside WikimediaClient; no DB or filesystem involvement |
| Fallback query retry | API / Backend (services) | — | Retry logic is a client responsibility; caller sees only the result |
| CDN image download (bytes) | API / Backend (services) | CDN / Static | Service downloads from Wikimedia CDN upload.wikimedia.org |
| Unit tests with mocked HTTP | Test harness | — | respx intercepts at transport layer; tests live in tests/unit/ |
| User-Agent header enforcement | API / Backend (services) | — | Wikimedia requires it per API etiquette policy; set on httpx.AsyncClient |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| httpx | 0.28.1 [VERIFIED: PyPI registry] | Async HTTP client for Wikimedia API calls and CDN download | Already in pyproject.toml dev deps; native async/await; first-class respx integration |
| respx | 0.23.1 [VERIFIED: PyPI registry] | Intercept httpx calls in tests | Already in pyproject.toml dev deps; transport-level mocking without patching |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| anyio | 4.13.0 [VERIFIED: PyPI registry] | Async primitives (already pulled in by httpx) | No new dependency; available via httpx's dependency graph |

### No new packages required

Both `httpx>=0.28.1` and `respx>=0.23.1` are already declared in `pyproject.toml`:

```toml
# [project.optional-dependencies].dev already contains:
"httpx>=0.28.1",
"respx>=0.23.1",
```

`httpx` must be added to `[project].dependencies` (production deps) since `WikimediaClient` is production code, not test code. Currently it only appears in dev deps.

**Version verification:** `pip index versions httpx` → 0.28.1 (current, matches installed). `pip index versions respx` → 0.23.1 (current, matches installed). Verified 2026-05-24.

---

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| httpx | PyPI | ~6 yrs | Very high (50M+/mo) | github.com/encode/httpx | OK | Approved (already in project) |
| respx | PyPI | ~5 yrs | High | github.com/lundberg/respx | OK | Approved (already in project) |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

*slopcheck 0.6.1 ran successfully on 2026-05-24 and returned OK for httpx, respx, and anyio.*

---

## Architecture Patterns

### System Architecture Diagram

```
[WikimediaClient.find_jpeg_url(brand, model, year)]
        │
        ├─── Step 1: Build primary query "{year} {brand} {model}"
        │
        ▼
[_search_first_jpeg(query)]
        │
        ├─── GET commons.wikimedia.org/w/api.php
        │      action=query
        │      generator=search
        │      gsrsearch={query}
        │      gsrnamespace=6               (File namespace)
        │      gsrlimit=10
        │      prop=imageinfo
        │      iiprop=url|mime
        │      iiurlwidth=800
        │      format=json
        │
        ▼
[Parse response: query.pages → values()]
        │
        ├─── Filter: mime == "image/jpeg"
        ├─── Sort by: index (search relevance)
        │
        ├─── JPEG found ──────────────────────→ return thumburl (str)
        │
        └─── No JPEG found (None)
                │
                ▼ (back in find_jpeg_url)
        ├─── Step 2: Build fallback query "{brand} {model}"
        │
        ▼
[_search_first_jpeg(fallback_query)]  (same logic)
        │
        ├─── JPEG found ──────────────────────→ return thumburl (str)
        │
        └─── No JPEG found ────────────────────→ return None

[Caller (Phase 5 ImageService)]
        │  receives thumburl: str | None
        │
        └─── if thumburl:
              GET upload.wikimedia.org/{thumburl}   ← step 3: CDN download
              → returns image bytes
```

### Recommended Project Structure

New files this phase creates:

```
src/carpix_images/
└── services/
    ├── storage.py              # Existing (Phase 2)
    └── wikimedia.py            # New: WikimediaClient class
tests/
└── unit/
    ├── test_storage.py         # Existing
    └── test_wikimedia.py       # New: unit tests with respx
```

No new packages, no new directories beyond `wikimedia.py` and its test file.

### Pattern 1: WikimediaClient — constructor with injected AsyncClient

**What:** The client takes `httpx.AsyncClient` as a constructor argument, enabling test injection and type safety.
**When to use:** Always — dependency injection is the project pattern (see `CacheRepository(engine)`).

```python
# Source: pattern consistent with CacheRepository(engine) in infrastructure/cache_repository.py
# [VERIFIED: project codebase]
from __future__ import annotations

import httpx

_COMMONS_API = "https://commons.wikimedia.org/w/api.php"


class WikimediaClient:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def find_jpeg_url(
        self, brand: str, model: str, year: int
    ) -> str | None:
        primary_query = f"{year} {brand} {model}"
        result = await self._search_first_jpeg(primary_query)
        if result is not None:
            return result

        fallback_query = f"{brand} {model}"
        return await self._search_first_jpeg(fallback_query)

    async def _search_first_jpeg(self, query: str) -> str | None:
        params = {
            "action": "query",
            "generator": "search",
            "gsrsearch": query,
            "gsrnamespace": "6",
            "gsrlimit": "10",
            "prop": "imageinfo",
            "iiprop": "url|mime",
            "iiurlwidth": "800",
            "format": "json",
        }
        response = await self._client.get(_COMMONS_API, params=params)
        response.raise_for_status()
        data = response.json()

        pages = data.get("query", {}).get("pages", {})
        # Sort by index (search relevance rank) to pick the most relevant JPEG
        candidates = sorted(pages.values(), key=lambda p: p.get("index", 999))
        for page in candidates:
            imageinfo = page.get("imageinfo", [])
            if not imageinfo:
                continue
            info = imageinfo[0]
            if info.get("mime") == "image/jpeg":
                thumburl: str = info["thumburl"]
                return thumburl
        return None
```

**mypy note:** `str | None` return type satisfies mypy strict. The `data.get()` chain returns `Any`, which is acceptable here since JSON parsing is inherently untyped. Use `# type: ignore[index]` where needed for dict key access on `Any`. [ASSUMED — exact mypy strict errors depend on runtime; pattern is consistent with project's existing `Any`-typed JSON parsing.]

### Pattern 2: User-Agent setup for the AsyncClient

**What:** Wikimedia API policy requires a meaningful User-Agent or the client risks IP block.
**When to use:** At construction time, before the client is injected into WikimediaClient.

```python
# Source: Wikimedia API Etiquette [CITED: https://www.mediawiki.org/wiki/API:Etiquette]
# Recommended format: "clientname/version (contact)"
USER_AGENT = "carpix-images/0.1 (https://github.com/user/carpix; carpix@example.com)"

client = httpx.AsyncClient(
    headers={"User-Agent": USER_AGENT},
    timeout=httpx.Timeout(10.0),
)
wikimedia_client = WikimediaClient(client)
```

The User-Agent can be hardcoded as a module-level constant in `wikimedia.py` or read from settings. The key requirement is that it is non-empty and meaningful (tool name + contact).

### Pattern 3: respx mock fixture for unit tests

**What:** `respx_mock` pytest fixture patches `httpx.AsyncClient._transport_for_url` globally, intercepting all httpx calls in the test function regardless of where the client is instantiated.
**When to use:** All unit tests for `WikimediaClient`. No `AsyncClient` subclassing needed.

```python
# Source: respx source (respx.plugin.respx_mock, respx.mocks.HTTPXMocker)
# [VERIFIED: project codebase - respx 0.23.1 installed]
import httpx
import pytest
import respx

from carpix_images.services.wikimedia import WikimediaClient


@pytest.fixture()
def wiki_client() -> WikimediaClient:
    return WikimediaClient(httpx.AsyncClient())


async def test_find_jpeg_url_returns_thumburl(
    wiki_client: WikimediaClient, respx_mock: respx.MockRouter
) -> None:
    respx_mock.get("https://commons.wikimedia.org/w/api.php").respond(
        200,
        json={
            "query": {
                "pages": {
                    "123": {
                        "pageid": 123,
                        "ns": 6,
                        "title": "File:Toyota_Corolla_2022.jpg",
                        "index": 1,
                        "imagerepository": "local",
                        "imageinfo": [
                            {
                                "thumburl": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/ab/Toyota_Corolla_2022.jpg/960px-Toyota_Corolla_2022.jpg",
                                "thumbwidth": 800,
                                "thumbheight": 450,
                                "url": "https://upload.wikimedia.org/wikipedia/commons/a/ab/Toyota_Corolla_2022.jpg",
                                "mime": "image/jpeg",
                            }
                        ],
                    }
                }
            }
        },
    )
    result = await wiki_client.find_jpeg_url("toyota", "corolla", 2022)
    assert result == "https://upload.wikimedia.org/wikipedia/commons/thumb/a/ab/Toyota_Corolla_2022.jpg/960px-Toyota_Corolla_2022.jpg"
```

**Important:** `respx_mock` fixture is sync (not async). The async test function itself is still `async def` and awaits the client method. The fixture just registers routes synchronously before the async body runs.

### Pattern 4: Testing the fallback query chain

**What:** When the first query returns no JPEG, the client must make a second call with the shorter query.
**When to use:** Test for WIKI-03.

```python
# Source: respx usage pattern [VERIFIED: respx 0.23.1]
async def test_fallback_query_used_when_primary_returns_no_jpeg(
    wiki_client: WikimediaClient, respx_mock: respx.MockRouter
) -> None:
    # Primary query: SVG only — no JPEG
    primary_route = respx_mock.get("https://commons.wikimedia.org/w/api.php").respond(
        200,
        json={
            "query": {
                "pages": {
                    "1": {
                        "pageid": 1,
                        "ns": 6,
                        "title": "File:Ford_Logo.svg",
                        "index": 1,
                        "imagerepository": "local",
                        "imageinfo": [{"mime": "image/svg+xml", "thumburl": "..."}],
                    }
                }
            }
        },
    )
    # NOTE: respx_mock with assert_all_called=True (default) requires all
    # registered routes to be called. For two calls to the same URL with
    # different params, use side_effect or register the route twice.
    # Simpler: use respx_mock with assert_all_called=False for this test,
    # or use respx.mock(assert_all_called=False) decorator.
    ...
```

**Respx param-matching note:** By default `respx_mock.get(url)` matches any GET to that URL regardless of query parameters. To distinguish primary vs fallback calls by `gsrsearch` param, use `respx_mock.get(url, params={"gsrsearch": "2022 toyota corolla", ...})`. For the fallback test, register two separate routes with different params and use `side_effect` for sequential responses. [ASSUMED — the exact respx param-matching API for query strings requires verification against respx 0.23.1 docs; the basic approach is confirmed.]

**Simpler alternative:** Use a `call_count` side-effect or use `respx.mock(assert_all_called=False)` and verify via `respx_mock.calls.call_count`.

### Pattern 5: Testing "no result" sentinel

**What:** When both queries fail, `find_jpeg_url` must return `None` without raising.
**When to use:** Test for WIKI-03 (tail case) and WIKI-04 (implied by success criterion 4).

```python
async def test_returns_none_when_no_jpeg_found(
    wiki_client: WikimediaClient, respx_mock: respx.MockRouter
) -> None:
    respx_mock.get("https://commons.wikimedia.org/w/api.php").respond(
        200,
        json={"query": {"pages": {}}},
    )
    result = await wiki_client.find_jpeg_url("nonexistent", "vehicle", 9999)
    assert result is None
```

### Anti-Patterns to Avoid

- **Manual thumburl construction:** Never build the CDN URL from file title or hash. The `thumburl` field from the API is authoritative and must be used directly (WIKI-01). Wikimedia CDN paths encode a content hash (`/thumb/a/ab/filename/Npx-filename`) that cannot be computed from title alone.
- **Filtering by file extension in title:** The title may say `.jpg` but be transcoded SVG, or a file may lack an extension. Always filter on `mime` field, never on title string.
- **Single query without fallback:** A year-specific query (`"2022 toyota corolla"`) frequently finds no results for niche vehicles. Always implement the two-query chain.
- **Returning the first result without mime check:** The first search result may be an SVG diagram or a PNG logo. Iterate all candidates filtered by `mime == "image/jpeg"` before giving up.
- **Not setting User-Agent:** Wikimedia API etiquette page states clients without a meaningful User-Agent "may be IP-blocked without notice". Always set a non-browser User-Agent on the `httpx.AsyncClient`.
- **Raising exceptions on empty results:** WIKI-03 success criterion 4 requires returning `None`, not raising. The caller (Phase 5 ImageService) converts `None` to HTTP 404.
- **Using `requests` or `urllib`:** Only httpx is used in this project (async requirement, respx integration).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP connection pooling | Custom asyncio socket pool | `httpx.AsyncClient` | httpx manages connection pool, timeouts, redirects, and keepalive automatically |
| Transport-level HTTP mocking | `unittest.mock.patch("httpx.AsyncClient.get")` | `respx` + `respx_mock` fixture | Method patching breaks type annotations, causes test isolation issues; respx patches at transport level so the full request lifecycle (headers, params, response parsing) is exercised |
| CDN thumbnail URL construction | Parse file title → build hash path | `thumburl` from imageinfo API | CDN path includes a content-hash segment that cannot be reproduced from the file title |
| Retry/backoff for rate limits | Custom sleep-retry loop | Wikimedia API has no enforced rate limit for this usage volume; httpx raises on 5xx which the caller handles | Out of scope per REQUIREMENTS.md |

**Key insight:** The Wikimedia API provides everything needed — search ranking, JPEG filtering via `mime`, and a ready-to-use `thumburl`. The client's job is purely to call the API correctly and extract the right field.

---

## Wikimedia Commons API Reference (VERIFIED)

### Step 1+2 Combined: Search + Imageinfo (single HTTP call)

**Endpoint:** `GET https://commons.wikimedia.org/w/api.php`

**Parameters:**

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `action` | `query` | Standard query action |
| `generator` | `search` | Use search as the page generator |
| `gsrsearch` | `{year} {brand} {model}` | Search query string (prefixed with `g`) |
| `gsrnamespace` | `6` | File namespace only [CITED: mediawiki.org/wiki/Help:Namespaces] |
| `gsrlimit` | `10` | Return up to 10 candidates |
| `prop` | `imageinfo` | Request image metadata for each page |
| `iiprop` | `url\|mime` | Request thumburl and mime type |
| `iiurlwidth` | `800` | Request thumbnail at ~800px width |
| `format` | `json` | JSON response |

**Response shape (confirmed via live API call 2026-05-24):**

```json
{
  "batchcomplete": "",
  "query": {
    "pages": {
      "{pageid}": {
        "pageid": 143599498,
        "ns": 6,
        "title": "File:Toyota Corolla Cross Hybrid 1X7A1861.jpg",
        "index": 1,
        "imagerepository": "local",
        "imageinfo": [
          {
            "thumburl": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0b/Toyota_Corolla_Cross_Hybrid_1X7A1861.jpg/960px-Toyota_Corolla_Cross_Hybrid_1X7A1861.jpg",
            "thumbwidth": 800,
            "thumbheight": 453,
            "responsiveUrls": { "2": "..." },
            "url": "https://upload.wikimedia.org/wikipedia/commons/0/0b/Toyota_Corolla_Cross_Hybrid_1X7A1861.jpg",
            "descriptionurl": "https://commons.wikimedia.org/wiki/File:Toyota_Corolla_Cross_Hybrid_1X7A1861.jpg",
            "descriptionshorturl": "...",
            "mime": "image/jpeg"
          }
        ]
      }
    }
  }
}
```

**Empty result shape (no matches):**

```json
{
  "batchcomplete": "",
  "query": {
    "pages": {}
  }
}
```

**Key observations (all VERIFIED via live API calls 2026-05-24):**
- `pages` is keyed by string pageid, not by integer
- `imageinfo` is always an array; `imageinfo[0]` is the current revision
- `thumburl` is present even for SVG and PNG files (SVG thumburl ends in `.png`)
- `mime` values observed: `"image/jpeg"`, `"image/png"`, `"image/svg+xml"`
- `iiurlwidth=800` causes Wikimedia to return a CDN standard size (observed: 960px in URL with `thumbwidth: 800`); the `thumburl` is what matters, not the URL's embedded pixel count
- `index` field is present when using generator=search; indicates search ranking order (1 = most relevant)
- When `query.pages` is missing entirely (no results at all), `data.get("query", {}).get("pages", {})` returns `{}` safely

### Step 3: CDN Download

**Request:** `GET {thumburl}` (from imageinfo response)

**No API key required.** User-Agent header recommended per Wikimedia etiquette.

**Response:** Raw JPEG bytes with `Content-Type: image/jpeg`.

---

## Common Pitfalls

### Pitfall 1: thumburl width in URL does not match iiurlwidth

**What goes wrong:** Developer inspects the `thumburl` and sees `960px` in the path when `iiurlwidth=800` was requested. They conclude the API is broken or write code to replace `960px` with `800px` in the URL string.
**Why it happens:** Wikimedia CDN serves images at predefined standard widths. `iiurlwidth=800` is interpreted as "at most 800px" but the CDN returns the next standard size up. The `thumbwidth` field in the response reports `800` (the requested width), while the URL contains `960px`.
**How to avoid:** Always use `thumburl` directly. Never parse or modify the URL. WIKI-01 is explicit: "uses it directly."
**Warning signs:** Code containing `thumburl.replace("960px", "800px")` — this is wrong and fragile.

### Pitfall 2: Missing User-Agent causes IP block

**What goes wrong:** Tests pass locally (Wikimedia is lenient with low traffic) but production calls start returning 403 or the IP gets blocked.
**Why it happens:** Wikimedia API policy requires a meaningful User-Agent. Requests without it are silently tolerated at low volume but flagged at scale.
**How to avoid:** Set a static `User-Agent` header on the `httpx.AsyncClient` at construction time. Use format: `"carpix-images/0.1 (contact@example.com)"`.
**Warning signs:** Intermittent 403 responses from `commons.wikimedia.org`.

### Pitfall 3: respx fixture vs. respx decorator — async test interaction

**What goes wrong:** Developer uses `@respx.mock` decorator on an `async def` test instead of the `respx_mock` fixture. In `asyncio_mode = "auto"` (project's pytest config), the decorator wraps the async function, but the interaction can cause event loop conflicts.
**Why it happens:** `pytest-asyncio` in auto mode and `@respx.mock` both wrap the test function. Using the `respx_mock` fixture avoids this wrapping conflict.
**How to avoid:** Use `respx_mock` as a pytest fixture parameter (already registered via respx's pytest plugin). Never use `@respx.mock` decorator in async tests.
**Warning signs:** `RuntimeError: no running event loop` or `ScopeMismatch` errors during test collection.

### Pitfall 4: assert_all_called fails when fallback path is not triggered

**What goes wrong:** A test registers two routes (primary + fallback) but the code only calls the primary (because it succeeded). respx's `assert_all_called=True` (default on `respx_mock` fixture) raises `AssertionError` because the fallback route was never called.
**Why it happens:** `respx_mock` default is `assert_all_called=True` — any registered route that was not called causes the assertion to fire at teardown.
**How to avoid:** For happy-path tests (primary query succeeds), only register the primary route. For fallback tests, design the test so both routes are actually called (primary returns no JPEG, fallback returns JPEG). Alternatively, use `@pytest.mark.respx(assert_all_called=False)` on individual tests.
**Warning signs:** `AssertionError: RESPX: ... was not called!` at test teardown.

### Pitfall 5: Empty pages dict vs. missing query key

**What goes wrong:** When Wikimedia returns no results at all, the response may be `{"batchcomplete": ""}` with no `"query"` key at all (not just an empty `pages` dict).
**Why it happens:** MediaWiki API omits the `query` key entirely when no pages match, rather than returning `{"query": {"pages": {}}}`.
**How to avoid:** Always use `data.get("query", {}).get("pages", {})` — two chained `.get()` calls with empty dict defaults — never `data["query"]["pages"]`.
**Warning signs:** `KeyError: 'query'` in production when a vehicle search returns zero results.

### Pitfall 6: httpx moved to production dependencies

**What goes wrong:** `WikimediaClient` is production code, but `httpx` is currently only in `[project.optional-dependencies].dev`. Deploying without dev extras causes `ModuleNotFoundError: No module named 'httpx'`.
**Why it happens:** The original pyproject.toml added httpx only for `TestClient` testing use. Production use of `httpx.AsyncClient` in `wikimedia.py` requires it in `[project].dependencies`.
**How to avoid:** Move `httpx>=0.28.1` to `[project].dependencies` in `pyproject.toml` as part of Wave 0 setup.
**Warning signs:** `ImportError` when running the app without `uv sync --extra dev`.

---

## Code Examples

### Full WikimediaClient implementation skeleton

```python
# Source: WIKI-01, WIKI-02, WIKI-03 requirements + live API verification 2026-05-24
from __future__ import annotations

import httpx

_COMMONS_API = "https://commons.wikimedia.org/w/api.php"
_USER_AGENT = "carpix-images/0.1 (https://github.com/user/carpix)"


class WikimediaClient:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def find_jpeg_url(
        self, brand: str, model: str, year: int
    ) -> str | None:
        """Return the first JPEG thumburl for the vehicle, or None."""
        primary = await self._search_first_jpeg(f"{year} {brand} {model}")
        if primary is not None:
            return primary
        return await self._search_first_jpeg(f"{brand} {model}")

    async def _search_first_jpeg(self, query: str) -> str | None:
        params = {
            "action": "query",
            "generator": "search",
            "gsrsearch": query,
            "gsrnamespace": "6",
            "gsrlimit": "10",
            "prop": "imageinfo",
            "iiprop": "url|mime",
            "iiurlwidth": "800",
            "format": "json",
        }
        response = await self._client.get(_COMMONS_API, params=params)
        response.raise_for_status()
        data: dict = response.json()  # type: ignore[assignment]

        pages = data.get("query", {}).get("pages", {})
        candidates = sorted(pages.values(), key=lambda p: p.get("index", 999))
        for page in candidates:
            imageinfo = page.get("imageinfo", [])
            if not imageinfo:
                continue
            info = imageinfo[0]
            if info.get("mime") == "image/jpeg":
                return str(info["thumburl"])
        return None
```

### AsyncClient factory with User-Agent (for use in lifespan or ImageService)

```python
# Pattern: construct WikimediaClient at app startup, store on app.state
# Source: httpx.AsyncClient headers param [VERIFIED: httpx 0.28.1 installed]
import httpx
from carpix_images.services.wikimedia import WikimediaClient, _USER_AGENT

def make_wikimedia_client() -> WikimediaClient:
    client = httpx.AsyncClient(
        headers={"User-Agent": _USER_AGENT},
        timeout=httpx.Timeout(10.0),
    )
    return WikimediaClient(client)
```

### Unit test: happy path

```python
# Source: respx 0.23.1 + pytest-asyncio asyncio_mode="auto"
import httpx
import pytest
import respx
from carpix_images.services.wikimedia import WikimediaClient


@pytest.fixture()
def wiki_client() -> WikimediaClient:
    return WikimediaClient(httpx.AsyncClient())


async def test_find_jpeg_url_primary_query(
    wiki_client: WikimediaClient, respx_mock: respx.MockRouter
) -> None:
    respx_mock.get("https://commons.wikimedia.org/w/api.php").respond(
        200,
        json={
            "query": {
                "pages": {
                    "1": {
                        "pageid": 1,
                        "ns": 6,
                        "title": "File:Toyota_Corolla_2022.jpg",
                        "index": 1,
                        "imagerepository": "local",
                        "imageinfo": [{
                            "thumburl": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/ab/Toyota_Corolla_2022.jpg/960px-Toyota_Corolla_2022.jpg",
                            "thumbwidth": 800,
                            "thumbheight": 450,
                            "mime": "image/jpeg",
                        }],
                    }
                }
            }
        },
    )
    result = await wiki_client.find_jpeg_url("toyota", "corolla", 2022)
    assert result is not None
    assert "upload.wikimedia.org" in result
```

### Unit test: JPEG filter skips SVG

```python
async def test_skips_svg_returns_none_when_no_jpeg(
    wiki_client: WikimediaClient, respx_mock: respx.MockRouter
) -> None:
    respx_mock.get("https://commons.wikimedia.org/w/api.php").respond(
        200,
        json={
            "query": {
                "pages": {
                    "1": {
                        "pageid": 1, "ns": 6, "title": "File:Ford_Logo.svg",
                        "index": 1, "imagerepository": "local",
                        "imageinfo": [{"mime": "image/svg+xml", "thumburl": "...svg.png"}],
                    }
                }
            }
        },
    )
    # Both primary and fallback get this SVG-only response
    result = await wiki_client.find_jpeg_url("ford", "f150", 2023)
    assert result is None
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Two separate API calls (search then imageinfo) | Combined `generator=search` + `prop=imageinfo` in one call | Available since MediaWiki API generators were introduced | Halves round-trips for the search+resolve phase |
| `requests` library (sync) | `httpx.AsyncClient` (async) | Project constraint from Phase 1 | No blocking; integrates with FastAPI's async event loop |
| Patching `httpx.get` with `unittest.mock` | `respx` transport-level mocking | respx ~0.17+ | Full request lifecycle tested; no patching fragility |
| Manual URL construction from file title | `thumburl` from imageinfo response | Always correct | CDN path includes content hash; construction from title is impossible |

**Deprecated/outdated:**
- Separate `list=search` + `prop=imageinfo` two-call pattern: Still works but unnecessary when `generator=search` + `prop=imageinfo` achieves the same in one call.
- `respx.MockTransport`: Deprecated in respx 0.23.x. Use `httpx.MockTransport(respx_router.handler)` directly or rely on the `respx_mock` fixture which uses transport patching instead.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | mypy strict will surface `Any` type errors from JSON dict access (`data.get(...)`) that require `# type: ignore[assignment]` or explicit casting | Code Examples | If wrong, the code is cleaner; never harmful to add explicit type annotations |
| A2 | `index` field is always present in generator=search results for ordering by relevance | Architecture Patterns, Code Examples | If `index` is absent in some edge case, sorting falls back to `key=999` which means the page still gets evaluated — no crash, but ordering may be unpredictable |
| A3 | respx 0.23.1 `respx_mock` fixture works correctly with pytest-asyncio 1.3.0 `asyncio_mode="auto"` | Pattern 3 | Both are already installed and in use in the project; confirmed no known incompatibility in changelog at time of research |

**If this table is empty:** All claims in this research were verified or cited — no user confirmation needed.

All three assumptions are low-risk: A1 is cosmetic, A2 has a safe fallback, A3 is validated by the existing project setup.

---

## Open Questions

1. **WikimediaClient lifecycle: constructed once or per-request?**
   - What we know: `CacheRepository` is constructed per-call site in Phase 5 with the engine from `app.state`. `httpx.AsyncClient` supports persistent connection pooling across requests when reused.
   - What's unclear: Whether `WikimediaClient` (and its inner `httpx.AsyncClient`) should be stored on `app.state` (created once in lifespan) or constructed fresh per request.
   - Recommendation: Store on `app.state` — reusing the `AsyncClient` enables connection keepalive to `commons.wikimedia.org`, reducing latency on repeated misses. Phase 5 (ImageService) will handle wiring. Phase 4 should focus only on the client logic; the lifespan wiring is a Phase 5 concern.

2. **Should `WikimediaClient` also download the image bytes (step 3)?**
   - What we know: Phase 4 goal is "resolve a vehicle query to a downloadable 800px JPEG URL." Phase 5 (ImageService) takes the URL and stores it via StorageService.
   - What's unclear: Whether step 3 (CDN download) belongs in `WikimediaClient` or in `ImageService`.
   - Recommendation: Keep `WikimediaClient` focused on URL resolution only (`find_jpeg_url` returns `str | None`). Add a separate `download(url: str) -> bytes` method or have `ImageService` do the download directly. The split keeps WikimediaClient unit-testable without byte-stream mocking. Phase 5 will decide.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| httpx | WikimediaClient HTTP calls | ✓ | 0.28.1 | — |
| respx | Unit test mocking | ✓ | 0.23.1 | — |
| Internet access (commons.wikimedia.org) | Integration/smoke tests only | ✓ | — | All automated tests use respx stubs; no live calls in CI |
| Python 3.12+ | `str | None` union syntax | ✓ | 3.13.6 | — |

**Missing dependencies with no fallback:** none

**Missing dependencies with fallback:** none

**One pyproject.toml change required:** Move `httpx>=0.28.1` from `[project.optional-dependencies].dev` to `[project].dependencies`.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 + pytest-asyncio 1.3.0 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (`asyncio_mode = "auto"`) |
| Quick run command | `python -m pytest tests/unit/test_wikimedia.py -x -q` |
| Full suite command | `python -m pytest tests/ -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| WIKI-01 | `find_jpeg_url` returns the `thumburl` string from imageinfo response exactly (not constructed) | unit | `python -m pytest tests/unit/test_wikimedia.py::test_find_jpeg_url_primary_query -x` | ❌ Wave 0 |
| WIKI-02a | SVG results (`mime: image/svg+xml`) are skipped | unit | `python -m pytest tests/unit/test_wikimedia.py::test_skips_svg -x` | ❌ Wave 0 |
| WIKI-02b | PNG results (`mime: image/png`) are skipped | unit | `python -m pytest tests/unit/test_wikimedia.py::test_skips_png -x` | ❌ Wave 0 |
| WIKI-02c | Only `mime: image/jpeg` candidates are selected when mixed types present | unit | `python -m pytest tests/unit/test_wikimedia.py::test_selects_jpeg_from_mixed -x` | ❌ Wave 0 |
| WIKI-03a | Fallback query `{brand} {model}` is used when primary returns no JPEG | unit | `python -m pytest tests/unit/test_wikimedia.py::test_fallback_query_called -x` | ❌ Wave 0 |
| WIKI-03b | Returns `None` (not exception) when both queries yield no JPEG | unit | `python -m pytest tests/unit/test_wikimedia.py::test_returns_none_when_no_result -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/unit/test_wikimedia.py -x -q`
- **Per wave merge:** `python -m pytest tests/unit/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `src/carpix_images/services/wikimedia.py` — stub with `NotImplementedError` (Wave 1)
- [ ] `tests/unit/test_wikimedia.py` — 6 failing unit tests (Wave 1 RED baseline)
- [ ] Move `httpx>=0.28.1` from dev deps to `[project].dependencies` in `pyproject.toml` (Wave 0 task)

*(No new test directories needed — `tests/unit/` already exists.)*

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Internal service; no user auth |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes | `gsrsearch` param passed via httpx `params=` dict — httpx URL-encodes it; no string interpolation into URL |
| V6 Cryptography | no | — |
| V7 Error Handling | yes | `response.raise_for_status()` + return `None` on empty result; never propagate unhandled exceptions to caller |

### Known Threat Patterns for httpx + Wikimedia API

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Query parameter injection via brand/model input | Tampering | httpx `params=` dict URL-encodes values automatically; never f-string into URL directly |
| SSRF via crafted thumburl | Elevation of Privilege | thumburl is fetched only after confirmed to be from `upload.wikimedia.org`; validate host before downloading in Phase 5 [ASSUMED — Phase 5 concern, but note the risk here] |
| Sensitive data in User-Agent | Information Disclosure | User-Agent contains only app name + contact URL; no secrets |

---

## Sources

### Primary (HIGH confidence)
- Live Wikimedia Commons API calls (2026-05-24) — confirmed response shapes for search+generator, imageinfo, mime field values, thumburl format, empty result shape
  - `https://commons.wikimedia.org/w/api.php?action=query&generator=search&...`
- respx 0.23.1 installed source — `respx.mocks.HTTPXMocker`, `respx.plugin.respx_mock` — confirmed transport-level patching mechanism
  [VERIFIED: project codebase]
- httpx 0.28.1 `AsyncClient.__init__` signature — confirmed `headers` parameter
  [VERIFIED: project codebase — `python3 -c "import httpx; help(httpx.AsyncClient.__init__)"`]
- MediaWiki namespace table — namespace 6 = File
  [CITED: https://www.mediawiki.org/wiki/Help:Namespaces]
- Wikimedia API Etiquette — User-Agent requirement
  [CITED: https://www.mediawiki.org/wiki/API:Etiquette]

### Secondary (MEDIUM confidence)
- MediaWiki API:Generator documentation — generator=search + prop=imageinfo pattern
  [CITED: https://www.mediawiki.org/wiki/API:Generator]
- MediaWiki API:Imageinfo documentation — iiprop, iiurlwidth parameters
  [CITED: https://www.mediawiki.org/wiki/API:Imageinfo]
- respx guide — MockTransport deprecation, `respx_mock` fixture usage
  [CITED: https://lundberg.github.io/respx/guide/]

### Tertiary (LOW confidence)
- none

---

## Metadata

**Confidence breakdown:**
- Wikimedia API (endpoints, response shapes): HIGH — verified via 6 live API calls in this session
- respx mocking patterns: HIGH — verified against installed respx 0.23.1 source code
- httpx AsyncClient configuration: HIGH — verified against installed httpx 0.28.1
- Fallback query pattern: HIGH — straightforward second call; no novel mechanism
- mypy strict compatibility: MEDIUM — pattern consistent with project; exact errors depend on runtime

**Research date:** 2026-05-24
**Valid until:** 2026-08-24 (Wikimedia API is stable; httpx and respx are mature libraries; MediaWiki generator API has been stable for years)
