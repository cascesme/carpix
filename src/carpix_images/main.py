from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from carpix_images.config import settings
from carpix_images.infrastructure.cache_repository import CacheRepository
from carpix_images.routers.health import router as health_router
from carpix_images.routers.images import router as images_router
from carpix_images.services.image_service import ImageService
from carpix_images.services.storage import StorageService
from carpix_images.services.wikimedia import WikimediaClient


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    engine: AsyncEngine = create_async_engine(settings.database_url)
    http_client: httpx.AsyncClient = httpx.AsyncClient()
    storage: StorageService = StorageService(settings.images_dir)
    repo: CacheRepository = CacheRepository(engine)
    wikimedia: WikimediaClient = WikimediaClient(http_client)
    image_service: ImageService = ImageService(
        storage=storage, repo=repo, wikimedia=wikimedia, http_client=http_client
    )
    app.state.engine = engine
    app.state.image_service = image_service
    try:
        yield
    finally:
        await engine.dispose()
        await http_client.aclose()


def create_app() -> FastAPI:
    application = FastAPI(
        title="carpix-images",
        version="1.0.0",
        lifespan=lifespan,
    )
    application.include_router(health_router)
    application.include_router(images_router)
    return application


app = create_app()
