import sys
import types
import pytest
from fastapi.testclient import TestClient

from routers import gpt_router
from app.services.product_service import product_service
from app.main import app, ERROR_MESSAGES
from auth import verify_gpt_token

client = TestClient(app)


class DummyAsyncSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

    async def run_sync(self, fn):
        # Simula la llamada síncrona dentro de la sesión
        return fn(None)


@pytest.mark.asyncio
async def test_search_products_in_db(monkeypatch):
    async def fake_search_products_async(db, **kwargs):
        return {"productos": [{"nombre": "Item"}]}

    # Simula el módulo db.AsyncSessionLocal()
    dummy_db = types.SimpleNamespace(AsyncSessionLocal=lambda: DummyAsyncSession())
    monkeypatch.setitem(sys.modules, "db", dummy_db)

    # Patch al método asincrónico que usa el servicio
    monkeypatch.setattr(product_service, "search_products_async", fake_search_products_async)

    results = await gpt_router.search_products_in_db("Item")
    assert results[0]["nombre"] == "Item"


def test_optimize_shopping_list_fetches_gpt_when_db_empty(monkeypatch):
    """Products missing in DB should be fetched via GPT preserving order."""
    # Override de token para poder llamar al endpoint
    app.dependency_overrides[verify_gpt_token] = lambda: "test-token"

    db_calls = []
    gpt_calls = []
    captured = {}

    async def fake_search_products_in_db(query, category=None):
        db_calls.append(query)
        mapping = {
            "apple": [{"nombre": "apple-db"}],
            "banana": [],
            "carrot": [{"nombre": "carrot-db"}],
        }
        return mapping[query]

    async def fake_search_products_with_gpt(query, category=None):
        gpt_calls.append(query)
        return [{"nombre": f"{query}-gpt"}]

    async def fake_optimize_purchases(products, location=None):
        captured["products"] = products
        return {"ok": True}

    monkeypatch.setattr(gpt_router, "search_products_in_db", fake_search_products_in_db)
    monkeypatch.setattr(gpt_router, "search_products_with_gpt", fake_search_products_with_gpt)
    monkeypatch.setattr(gpt_router, "optimize_purchases", fake_optimize_purchases)

    response = client.post(
        "/api/optimize", json={"products": ["apple", "banana", "carrot"]}
    )

    assert response.status_code == 200
    assert db_calls == ["apple", "banana", "carrot"]
    assert gpt_calls == ["banana"]
    assert captured["products"] == [
        {"nombre": "apple-db"},
        {"nombre": "banana-gpt"},
        {"nombre": "carrot-db"},
    ]

    # Limpia el override
    del app.dependency_overrides[verify_gpt_token]


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

    # Llamamos directamente al helper de búsqueda con contexto
    await gpt_router.search_products(query="pan", user_id="user123", token="test-token")
    assert "peanut" in captured["prompt"]

