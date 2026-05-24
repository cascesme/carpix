"""Integration tests for GET /v1/images/{brand}/{model}/{year}."""

from __future__ import annotations

import asyncio
import os
import shutil
from collections.abc import AsyncGenerator

import asyncpg
import pytest
import respx
from alembic.config import Config
from httpx import ASGITransport, AsyncClient

from alembic import command
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
    """Run migrations and reset state for a clean test environment."""
    command.upgrade(_alembic_cfg(), "head")

    # Truncate vehicle_images table to ensure a clean state for router tests.
    # The cache_repository integration tests may have pre-populated rows.
    async def _truncate() -> None:
        url = os.environ["DATABASE_URL"].replace(
            "postgresql+asyncpg://", "postgresql://"
        )
        conn = await asyncpg.connect(url)
        try:
            await conn.execute("TRUNCATE TABLE vehicle_images")
        finally:
            await conn.close()

    asyncio.run(_truncate())

    # Clean cached images to avoid stale HIT responses from prior test runs.
    images_dir = os.environ.get("IMAGES_DIR", "/tmp/carpix_test_images")
    if os.path.isdir(images_dir):
        shutil.rmtree(images_dir)


@pytest.fixture()
async def client() -> AsyncGenerator[AsyncClient, None]:
    from carpix_images.config import settings as app_settings

    app_settings.database_url = os.environ["DATABASE_URL"]  # type: ignore[misc]
    application = create_app()
    async with application.router.lifespan_context(application):
        async with AsyncClient(
            transport=ASGITransport(app=application),  # type: ignore[arg-type]
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
