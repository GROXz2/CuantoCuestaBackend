import pytest
from unittest.mock import AsyncMock

from app.api.v1.routers import health


class DummyRedis:
    async def ping(self):
        return True


@pytest.mark.asyncio
async def test_check_redis_connects_when_client_missing(monkeypatch):
    cache = health.cache
    cache.redis_client = None

    async def connect():
        cache.redis_client = DummyRedis()

    monkeypatch.setattr(cache, "_connect", AsyncMock(side_effect=connect))

    assert await health.check_redis() is True
    cache._connect.assert_awaited_once()

    cache.redis_client = None
