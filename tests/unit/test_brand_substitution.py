import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from brand_substitution import suggest_substitutions

app = FastAPI()
MAPPING = {"A": ["B", "C"]}


@app.get("/brand/{brand}")
async def brand_endpoint(brand: str):
    return {"alternatives": suggest_substitutions(brand, MAPPING)}


@pytest.mark.asyncio
async def test_brand_substitution_found():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/brand/A")
    assert response.status_code == 200
    assert response.json() == {"alternatives": ["B", "C"]}


@pytest.mark.asyncio
async def test_brand_substitution_not_found():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/brand/Z")
    assert response.status_code == 200
    assert response.json() == {"alternatives": []}
