import pytest
from fastapi import FastAPI, Body
from httpx import AsyncClient

from ocr_service import extract_text

app = FastAPI()


@app.post("/ocr")
async def ocr_endpoint(payload: bytes = Body(...)):
    text = await extract_text(payload)
    return {"text": text}


@pytest.mark.asyncio
async def test_extract_text_via_api():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            "/ocr",
            content=b"hola",
            headers={"Content-Type": "application/octet-stream"},
        )
    assert response.status_code == 200
    assert response.json() == {"text": "hola"}
