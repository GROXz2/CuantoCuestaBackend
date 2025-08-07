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


def test_optimize_shopping_list_fetches_gpt_when_db_empty(client, monkeypatch):
    """Products missing in DB should be fetched via GPT preserving order."""

    from app.main import app
    from auth import verify_gpt_token

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

    del app.dependency_overrides[verify_gpt_token]
