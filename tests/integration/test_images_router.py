"""Integration tests for GET /v1/images/{brand}/{model}/{year} — RED baseline for Phase 6."""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator

import pytest
import respx
import httpx
from alembic import command
from alembic.config import Config
from httpx import AsyncClient, ASGITransport

from carpix_images.main import create_app

pytestmark = pytest.mark.usefixtures("postgres_container")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FAKE_JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 100
COMMONS_SEARCH_URL = "https://commons.wikimedia.org/w/api.php"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _alembic_cfg() -> Config:
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])
    return cfg


def _stub_wikimedia_success(respx_mock: respx.MockRouter, thumb_url: str) -> None:
    """Stub both Wikimedia API search and CDN thumbnail download."""
    respx_mock.get(COMMONS_SEARCH_URL).respond(
        200,
        json={
            "query": {
                "pages": {
                    "1": {
                        "index": 1,
                        "imageinfo": [{"thumburl": thumb_url, "mime": "image/jpeg"}],
                    }
                }
            }
        },
    )
    respx_mock.get(thumb_url).respond(
        200,
        content=FAKE_JPEG,
        headers={"content-type": "image/jpeg"},
    )


def _stub_wikimedia_no_result(respx_mock: respx.MockRouter) -> None:
    """Stub Wikimedia API to return empty search results for any call."""
    respx_mock.get(COMMONS_SEARCH_URL).respond(
        200,
        json={"query": {"pages": {}}},
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module", autouse=True)
def run_migrations() -> None:
    command.upgrade(_alembic_cfg(), "head")


@pytest.fixture(scope="module")
def app() -> object:
    return create_app()


@pytest.fixture()
async def client(app: object) -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=app),  # type: ignore[arg-type]
        base_url="http://test",
    ) as c:
        yield c


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_cache_miss_returns_jpeg_with_x_cache_miss_header(
    client: AsyncClient,
    respx_mock: respx.MockRouter,
) -> None:
    """GET first request → 200, X-Cache: MISS, content-type: image/jpeg."""
    thumb = "https://upload.wikimedia.org/thumb/sample.jpg"
    _stub_wikimedia_success(respx_mock, thumb)
    r = await client.get("/v1/images/toyota/corolla/2022")
    assert r.status_code == 200
    assert r.headers["x-cache"] == "MISS"
    assert r.headers["content-type"].startswith("image/jpeg")


async def test_cache_hit_returns_jpeg_with_x_cache_hit_header(
    client: AsyncClient,
    respx_mock: respx.MockRouter,
) -> None:
    """Two consecutive GETs → second response X-Cache: HIT."""
    thumb = "https://upload.wikimedia.org/thumb/sample.jpg"
    _stub_wikimedia_success(respx_mock, thumb)
    r1 = await client.get("/v1/images/honda/civic/2021")
    assert r1.status_code == 200
    r2 = await client.get("/v1/images/honda/civic/2021")
    assert r2.status_code == 200
    assert r2.headers["x-cache"] == "HIT"


async def test_no_wikimedia_result_returns_404(
    client: AsyncClient,
    respx_mock: respx.MockRouter,
) -> None:
    """Wikimedia returns empty results → 404 with detail message."""
    _stub_wikimedia_no_result(respx_mock)
    r = await client.get("/v1/images/nonexistent/vehicle/9999")
    assert r.status_code == 404
    assert r.json() == {"detail": "No image found for this vehicle"}


async def test_brand_model_normalized_in_path(
    client: AsyncClient,
    respx_mock: respx.MockRouter,
) -> None:
    """Mixed-case and URL-encoded model → normalization works, X-Cache: MISS."""
    thumb = "https://upload.wikimedia.org/thumb/normalized.jpg"
    _stub_wikimedia_success(respx_mock, thumb)
    r = await client.get("/v1/images/Toyota/Corolla%20Sport/2022")
    assert r.status_code == 200
    assert r.headers["x-cache"] == "MISS"


async def test_content_type_is_image_jpeg(
    client: AsyncClient,
    respx_mock: respx.MockRouter,
) -> None:
    """Any successful response has content-type: image/jpeg."""
    thumb = "https://upload.wikimedia.org/thumb/ct_test.jpg"
    _stub_wikimedia_success(respx_mock, thumb)
    r = await client.get("/v1/images/ford/mustang/2020")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("image/jpeg")
