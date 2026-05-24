from __future__ import annotations

from typing import cast

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse

from carpix_images.services.image_service import ImageService

router = APIRouter()


@router.get("/v1/images/{brand}/{model}/{year}")
async def get_image(
    brand: str, model: str, year: int, request: Request
) -> FileResponse:
    svc = cast(ImageService, request.app.state.image_service)
    response, cache_hit = await svc.get_or_fetch(brand, model, year)
    response.headers["X-Cache"] = "HIT" if cache_hit else "MISS"
    return response
