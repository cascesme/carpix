from __future__ import annotations

from pathlib import Path

from fastapi.responses import FileResponse


class StorageService:
    def __init__(self, base_dir: Path) -> None:
        self._base = base_dir.resolve()

    def _validated_path(
        self, brand_key: str, model_key: str, year: int
    ) -> Path:
        raise NotImplementedError

    async def save(
        self, brand_key: str, model_key: str, year: int, data: bytes
    ) -> Path:
        raise NotImplementedError

    def file_response(
        self, brand_key: str, model_key: str, year: int
    ) -> FileResponse:
        raise NotImplementedError
