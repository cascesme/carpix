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
        raise NotImplementedError

    async def _search_first_jpeg(self, query: str) -> str | None:
        raise NotImplementedError
