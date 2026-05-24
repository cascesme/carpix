from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse

router = APIRouter()


@router.get("/v1/images/{brand}/{model}/{year}")
async def get_image(
    brand: str, model: str, year: int, request: Request
) -> FileResponse:
    raise NotImplementedError
