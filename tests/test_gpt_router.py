import sys
import types
import pytest

from routers import gpt_router
from app.services.product_service import product_service


class DummyAsyncSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

    async def run_sync(self, fn):
        return fn(None)


@pytest.mark.asyncio
async def test_search_products_in_db(monkeypatch):
    async def fake_search_products_async(db, **kwargs):
        return {"productos": [{"nombre": "Item"}]}

    dummy_db = types.SimpleNamespace(AsyncSessionLocal=lambda: DummyAsyncSession())
    monkeypatch.setitem(sys.modules, "db", dummy_db)
    monkeypatch.setattr(product_service, "search_products_async", fake_search_products_async)

    results = await gpt_router.search_products_in_db("Item")
    assert results[0]["nombre"] == "Item"


@pytest.mark.asyncio
async def test_search_products_includes_allergy_context(monkeypatch):
    """Ensures allergy context is passed to GPT prompt."""

    async def fake_search_products_in_db(query, category=None):
        return []

    captured = {}

    async def fake_consulta_gpt(prompt):
        captured["prompt"] = prompt
        return "[]"

    class DummyConversationService:
        async def get_user_context_summary(self, user_id):
            return {
                "user_id": user_id,
                "context_summary": {
                    "preference_profile": {
                        "allergies": ["peanut"],
                        "dietary_restrictions": []
                    }
                },
                "profile_exists": True
            }

    monkeypatch.setattr(gpt_router, "search_products_in_db", fake_search_products_in_db)
    monkeypatch.setattr(gpt_router, "consulta_gpt", fake_consulta_gpt)
    monkeypatch.setattr(gpt_router, "ConversationService", lambda: DummyConversationService())

    await gpt_router.search_products(query="pan", user_id="user123", token="")
    assert "peanut" in captured["prompt"]
