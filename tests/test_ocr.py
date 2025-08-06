"""Tests para el servicio y endpoint OCR"""
import base64
from fastapi.testclient import TestClient

from app.services.ocr_service import OCRService, ocr_service
from tests.conftest import TestUtils


SAMPLE_IMAGE_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMB/6n+hKgAAAAASUVORK5CYII="
)


def _get_sample_image_bytes() -> bytes:
    return base64.b64decode(SAMPLE_IMAGE_BASE64)


class TestOCRService:
    """Tests para utilidades del servicio OCR"""

    def test_normalize_text(self):
        service = OCRService()
        text = "Árbol Ñandú"
        assert service.normalize_text(text) == "ARBOL NANDU"


class TestOCREndpoint:
    """Tests para el endpoint de OCR"""

    def test_ocr_lista(self, client: TestClient, sample_product, monkeypatch):
        image_bytes = _get_sample_image_bytes()

        async def mock_extract(image_bytes_param, db):
            return [{"id": str(sample_product.id), "nombre": sample_product.name}]

        monkeypatch.setattr(
            ocr_service, "extract_products_from_image", mock_extract
        )

        files = {"images": ("test.png", image_bytes, "image/png")}
        response = client.post("/api/v1/ocr/lista", files=files)

        TestUtils.assert_response_success(response)
        data = response.json()
        assert data["productos"][0]["nombre"] == sample_product.name
