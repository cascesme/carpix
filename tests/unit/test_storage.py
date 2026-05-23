from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.responses import FileResponse

from carpix_images.services.storage import StorageService


class TestStorageServiceSave:
    async def test_save_writes_file_at_correct_path(self, tmp_path: Path) -> None:
        svc = StorageService(tmp_path)
        await svc.save("toyota", "camry", 2020, b"FAKE_JPEG")
        expected = tmp_path / "toyota" / "camry" / "2020" / "image.jpg"
        assert expected.exists() is True
        assert expected.read_bytes() == b"FAKE_JPEG"

    async def test_save_creates_intermediate_directories(self, tmp_path: Path) -> None:
        svc = StorageService(tmp_path)
        await svc.save("byddmi", "sealudmi", 2023, b"DATA")
        assert (tmp_path / "byddmi" / "sealudmi" / "2023").is_dir() is True

    async def test_save_is_idempotent(self, tmp_path: Path) -> None:
        svc = StorageService(tmp_path)
        await svc.save("toyota", "camry", 2020, b"FIRST")
        await svc.save("toyota", "camry", 2020, b"SECOND")
        result = (tmp_path / "toyota" / "camry" / "2020" / "image.jpg").read_bytes()
        assert result == b"SECOND"


class TestStorageServiceFileResponse:
    def test_valid_path_returns_file_response(self, tmp_path: Path) -> None:
        svc = StorageService(tmp_path)
        (tmp_path / "toyota" / "camry" / "2020").mkdir(parents=True)
        (tmp_path / "toyota" / "camry" / "2020" / "image.jpg").write_bytes(b"DATA")
        resp = svc.file_response("toyota", "camry", 2020)
        assert isinstance(resp, FileResponse)

    def test_traversal_attempt_raises_value_error(self, tmp_path: Path) -> None:
        svc = StorageService(tmp_path)
        with pytest.raises(ValueError, match="traversal"):
            svc.file_response("..", "..", 2020)
