from __future__ import annotations

from pathlib import Path

import anyio
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
        target_dir = anyio.Path(self._base) / brand_key / model_key / str(year)
        await target_dir.mkdir(parents=True, exist_ok=True)
        target_file = target_dir / "image.jpg"
        await target_file.write_bytes(data)
        return Path(target_file)

    def file_response(
        self, brand_key: str, model_key: str, year: int
    ) -> FileResponse:
        raise NotImplementedError
