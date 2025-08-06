"""
Tests para endpoints de precios
"""
import pytest
from fastapi.testclient import TestClient
from tests.conftest import TestUtils


class TestPriceEndpoints:
    """Tests para comparación de precios"""

    def test_comparar_precios_sin_sugerencia(self, client: TestClient, sample_product, sample_price):
        """No debe sugerir marca cuando hay stock"""
        response = client.get(f"/api/v1/precios/comparar/{sample_product.id}")

        TestUtils.assert_response_success(response)
        data = response.json()
        assert data["precios"]
        assert "marca_sugerida" not in data

    def test_comparar_precios_con_sugerencia(
        self,
        client: TestClient,
        sample_product,
        sample_product_alt,
        sample_price_alt,
    ):
        """Debe sugerir marca alternativa cuando no hay stock"""
        response = client.get(f"/api/v1/precios/comparar/{sample_product.id}")

        TestUtils.assert_response_success(response)
        data = response.json()
        assert data["precios"] == []
        assert data["marca_sugerida"] == "Alternative Brand"
        assert "Alternative Brand" in data["explicacion"]
