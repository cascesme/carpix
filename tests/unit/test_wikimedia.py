"""Unit tests for WikimediaClient — covers WIKI-01, WIKI-02, WIKI-03."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import httpx
import pytest
import respx

from carpix_images.services.wikimedia import WikimediaClient

_API_URL = "https://commons.wikimedia.org/w/api.php"


@pytest.fixture()
async def wiki_client() -> AsyncGenerator[WikimediaClient, None]:
    async with httpx.AsyncClient() as client:
        yield WikimediaClient(client)


async def test_find_jpeg_url_returns_thumburl_exactly(
    wiki_client: WikimediaClient, respx_mock: respx.MockRouter
) -> None:
    respx_mock.get(_API_URL).respond(
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
                                "mime": "image/jpeg",
                            }
                        ],
                    }
                }
            }
        },
    )
    result = await wiki_client.find_jpeg_url("toyota", "corolla", 2022)
    assert (
        result
        == "https://upload.wikimedia.org/wikipedia/commons/thumb/a/ab/Toyota_Corolla_2022.jpg/960px-Toyota_Corolla_2022.jpg"
    )


@pytest.mark.respx(assert_all_called=False)
async def test_skips_svg_and_returns_none(
    wiki_client: WikimediaClient, respx_mock: respx.MockRouter
) -> None:
    respx_mock.get(_API_URL).respond(
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
                        "imageinfo": [
                            {"mime": "image/svg+xml", "thumburl": "...svg.png"}
                        ],
                    }
                }
            }
        },
    )
    result = await wiki_client.find_jpeg_url("ford", "f150", 2023)
    assert result is None


@pytest.mark.respx(assert_all_called=False)
async def test_skips_png_and_returns_none(
    wiki_client: WikimediaClient, respx_mock: respx.MockRouter
) -> None:
    respx_mock.get(_API_URL).respond(
        200,
        json={
            "query": {
                "pages": {
                    "1": {
                        "pageid": 1,
                        "ns": 6,
                        "title": "File:Honda_Civic_Logo.png",
                        "index": 1,
                        "imagerepository": "local",
                        "imageinfo": [{"mime": "image/png", "thumburl": "...png.png"}],
                    }
                }
            }
        },
    )
    result = await wiki_client.find_jpeg_url("honda", "civic", 2021)
    assert result is None


async def test_selects_jpeg_from_mixed_types(
    wiki_client: WikimediaClient, respx_mock: respx.MockRouter
) -> None:
    respx_mock.get(_API_URL).respond(
        200,
        json={
            "query": {
                "pages": {
                    "1": {
                        "pageid": 1,
                        "ns": 6,
                        "title": "File:BMW_Logo.svg",
                        "index": 1,
                        "imagerepository": "local",
                        "imageinfo": [
                            {"mime": "image/svg+xml", "thumburl": "...svg.png"}
                        ],
                    },
                    "2": {
                        "pageid": 2,
                        "ns": 6,
                        "title": "File:BMW_3_Series_2022.jpg",
                        "index": 2,
                        "imagerepository": "local",
                        "imageinfo": [
                            {
                                "mime": "image/jpeg",
                                "thumburl": "https://upload.wikimedia.org/jpeg.jpg",
                            }
                        ],
                    },
                }
            }
        },
    )
    result = await wiki_client.find_jpeg_url("bmw", "3series", 2022)
    assert result == "https://upload.wikimedia.org/jpeg.jpg"


async def test_fallback_query_called_when_primary_returns_no_jpeg(
    wiki_client: WikimediaClient, respx_mock: respx.MockRouter
) -> None:
    primary_response = httpx.Response(
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
                        "imageinfo": [
                            {"mime": "image/svg+xml", "thumburl": "...svg.png"}
                        ],
                    }
                }
            }
        },
    )
    fallback_response = httpx.Response(
        200,
        json={
            "query": {
                "pages": {
                    "2": {
                        "pageid": 2,
                        "ns": 6,
                        "title": "File:Ford_Mustang.jpg",
                        "index": 1,
                        "imagerepository": "local",
                        "imageinfo": [
                            {
                                "mime": "image/jpeg",
                                "thumburl": "https://upload.wikimedia.org/fallback.jpg",
                            }
                        ],
                    }
                }
            }
        },
    )
    respx_mock.get(_API_URL).mock(side_effect=[primary_response, fallback_response])
    result = await wiki_client.find_jpeg_url("ford", "mustang", 2019)
    assert result == "https://upload.wikimedia.org/fallback.jpg"
    assert respx_mock.calls.call_count == 2


async def test_returns_none_when_all_strategies_yield_no_jpeg(
    wiki_client: WikimediaClient, respx_mock: respx.MockRouter
) -> None:
    empty_response = httpx.Response(200, json={"query": {"pages": {}}})
    respx_mock.get(_API_URL).mock(
        side_effect=[empty_response, empty_response, empty_response]
    )
    result = await wiki_client.find_jpeg_url("nonexistent", "vehicle", 9999)
    assert result is None
    assert respx_mock.calls.call_count == 3


async def test_invalid_title_skips_candidate_uses_next(
    wiki_client: WikimediaClient, respx_mock: respx.MockRouter
) -> None:
    respx_mock.get(_API_URL).respond(
        200,
        json={
            "query": {
                "pages": {
                    "1": {
                        "pageid": 1,
                        "ns": 6,
                        "title": "File:Ferrari_488_interior.jpg",
                        "index": 1,
                        "imagerepository": "local",
                        "imageinfo": [
                            {
                                "mime": "image/jpeg",
                                "thumburl": "https://upload.wikimedia.org/interior.jpg",
                            }
                        ],
                    },
                    "2": {
                        "pageid": 2,
                        "ns": 6,
                        "title": "File:Ferrari_488_Spider_2019.jpg",
                        "index": 2,
                        "imagerepository": "local",
                        "imageinfo": [
                            {
                                "mime": "image/jpeg",
                                "thumburl": "https://upload.wikimedia.org/spider.jpg",
                            }
                        ],
                    },
                }
            }
        },
    )
    result = await wiki_client.find_jpeg_url("ferrari", "488", 2019)
    assert result == "https://upload.wikimedia.org/spider.jpg"


async def test_all_candidates_invalid_falls_to_next_strategy(
    wiki_client: WikimediaClient, respx_mock: respx.MockRouter
) -> None:
    bad_response = httpx.Response(
        200,
        json={
            "query": {
                "pages": {
                    "1": {
                        "pageid": 1,
                        "ns": 6,
                        "title": "File:BMW_3series_plan_in_BMW-Museum.jpg",
                        "index": 1,
                        "imagerepository": "local",
                        "imageinfo": [
                            {
                                "mime": "image/jpeg",
                                "thumburl": "https://upload.wikimedia.org/museum.jpg",
                            }
                        ],
                    }
                }
            }
        },
    )
    good_response = httpx.Response(
        200,
        json={
            "query": {
                "pages": {
                    "2": {
                        "pageid": 2,
                        "ns": 6,
                        "title": "File:BMW_3_Series_2020.jpg",
                        "index": 1,
                        "imagerepository": "local",
                        "imageinfo": [
                            {
                                "mime": "image/jpeg",
                                "thumburl": "https://upload.wikimedia.org/coupe.jpg",
                            }
                        ],
                    }
                }
            }
        },
    )
    respx_mock.get(_API_URL).mock(side_effect=[bad_response, good_response])
    result = await wiki_client.find_jpeg_url("bmw", "3series", 2020)
    assert result == "https://upload.wikimedia.org/coupe.jpg"
    assert respx_mock.calls.call_count == 2


async def test_third_strategy_exterior_tried(
    wiki_client: WikimediaClient, respx_mock: respx.MockRouter
) -> None:
    empty = httpx.Response(200, json={"query": {"pages": {}}})
    good_response = httpx.Response(
        200,
        json={
            "query": {
                "pages": {
                    "1": {
                        "pageid": 1,
                        "ns": 6,
                        "title": "File:Honda_Civic_2021.jpg",
                        "index": 1,
                        "imagerepository": "local",
                        "imageinfo": [
                            {
                                "mime": "image/jpeg",
                                "thumburl": "https://upload.wikimedia.org/civic.jpg",
                            }
                        ],
                    }
                }
            }
        },
    )
    respx_mock.get(_API_URL).mock(side_effect=[empty, empty, good_response])
    result = await wiki_client.find_jpeg_url("honda", "civic", 2021)
    assert result == "https://upload.wikimedia.org/civic.jpg"
    assert respx_mock.calls.call_count == 3
