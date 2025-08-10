import pytest
from fastapi import FastAPI
from unittest.mock import AsyncMock, MagicMock

import app.main as app_main
from app.core.config import settings


@pytest.mark.asyncio
async def test_startup_fails_on_localhost_in_production(monkeypatch):
    monkeypatch.setattr(settings, "DEBUG", False)
    monkeypatch.setattr(settings, "REDIS_URL", "redis://localhost:6379/0")
    with pytest.raises(RuntimeError):
        async with app_main.lifespan(FastAPI()):
            pass


@pytest.mark.asyncio
async def test_limiter_initialized_with_client(monkeypatch):
    class DummyRedis:
        async def ping(self):
            return True

        async def close(self):
            pass

    redis_instance = DummyRedis()

    def dummy_from_url(url, *args, **kwargs):
        return redis_instance

    limiter = MagicMock()
    limiter.init = AsyncMock()

    monkeypatch.setattr(app_main, "FastAPILimiter", limiter)
    monkeypatch.setattr(app_main.aioredis, "from_url", dummy_from_url)
    monkeypatch.setattr(settings, "REDIS_URL", "redis://example:6379/0")

    async with app_main.lifespan(app_main.app):
        pass

    limiter.init.assert_awaited_once_with(redis_instance)
