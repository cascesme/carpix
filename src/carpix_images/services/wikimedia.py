from __future__ import annotations

from typing import Any

import httpx

from carpix_images.domain.validate import is_valid_candidate

_COMMONS_API = "https://commons.wikimedia.org/w/api.php"
_USER_AGENT = "carpix-images/0.1 (https://github.com/user/carpix)"


class WikimediaClient:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def find_jpeg_url(self, brand: str, model: str, year: int) -> str | None:
        strategies = [
            f"{year} {brand} {model}",
            f"{brand} {model}",
            f"{brand} {model} exterior",
        ]
        for query in strategies:
            url = await self._search_valid_jpeg(query, brand, model)
            if url is not None:
                return url
        return None

    async def _search_valid_jpeg(
        self, query: str, brand: str, model: str
    ) -> str | None:
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
        try:
            response = await self._client.get(
                _COMMONS_API, params=params, headers={"User-Agent": _USER_AGENT}
            )
            response.raise_for_status()
        except (httpx.HTTPStatusError, httpx.RequestError):
            return None
        data: dict[str, Any] = response.json()

        pages: dict[str, Any] = data.get("query", {}).get("pages", {})
        candidates: list[Any] = sorted(
            pages.values(), key=lambda p: p.get("index", 999)
        )
        for page in candidates:
            imageinfo: list[Any] = page.get("imageinfo", [])
            if not imageinfo:
                continue
            info: dict[str, Any] = imageinfo[0]
            thumb = info.get("thumburl")
            if not thumb or info.get("mime") != "image/jpeg":
                continue
            if not is_valid_candidate(page.get("title", ""), brand, model):
                continue
            return str(thumb)
        return None
