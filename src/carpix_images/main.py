from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from carpix_images.routers.health import router as health_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Phase 1: no-op. Phase 3 will wire asyncpg pool here.
    yield


def create_app() -> FastAPI:
    application = FastAPI(
        title="carpix-images",
        version="1.0.0",
        lifespan=lifespan,
    )
    application.include_router(health_router)
    return application


app = create_app()
