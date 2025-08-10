import asyncio

from fastapi import APIRouter

from app.core.cache import cache
from app.core.database import check_database_connection

router = APIRouter(tags=["Health"])


async def check_db(timeout: float = 1.0) -> bool:
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(check_database_connection), timeout
        )
    except Exception:
        return False


async def check_redis(timeout: float = 1.0) -> bool:
    if not cache.redis_client:
        return False
    try:
        return await asyncio.wait_for(cache.redis_client.ping(), timeout)
    except Exception:
        return False


@router.get("/health")
async def health() -> dict:
    db_ok, redis_ok = await asyncio.gather(check_db(), check_redis())
    status = "ok" if db_ok and redis_ok else "degraded"
    return {
        "status": status,
        "database": "ok" if db_ok else "error",
        "redis": "ok" if redis_ok else "error",
    }
