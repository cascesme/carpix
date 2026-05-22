import asyncpg
from fastapi import APIRouter

from carpix_images.config import settings

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    db_status = "error"
    dsn = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    try:
        conn = await asyncpg.connect(dsn, timeout=3)
        await conn.execute("SELECT 1")
        await conn.close()
        db_status = "ok"
    except Exception:
        pass
    return {"status": "ok", "db": db_status}
