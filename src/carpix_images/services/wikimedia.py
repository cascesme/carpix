from __future__ import annotations

from typing import Any

import httpx

_COMMONS_API = "https://commons.wikimedia.org/w/api.php"
_USER_AGENT = "carpix-images/0.1 (https://github.com/user/carpix)"


class WikimediaClient:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def find_jpeg_url(
        self, brand: str, model: str, year: int
    ) -> str | None:
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
        response = await self._client.get(
            _COMMONS_API, params=params, headers={"User-Agent": _USER_AGENT}
        )
        response.raise_for_status()
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
            if info.get("mime") == "image/jpeg":
                return str(info["thumburl"])
        return None
