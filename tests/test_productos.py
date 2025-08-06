"""
Tests para endpoints de productos
"""
import pytest
from fastapi.testclient import TestClient
from tests.conftest import TestUtils


class TestProductsEndpoints:
    """Tests para endpoints de productos"""
    
    def test_buscar_productos_success(self, client: TestClient, sample_product):
        """Test búsqueda exitosa de productos"""
        response = client.get("/api/v1/productos/buscar?q=Test")
        
        TestUtils.assert_response_success(response)
        data = response.json()
        
        assert "productos" in data
        assert "total" in data
        assert "termino_busqueda" in data
        assert data["termino_busqueda"] == "Test"
        assert isinstance(data["productos"], list)
    
    def test_buscar_productos_empty_query(self, client: TestClient):
        """Test búsqueda con query vacío"""
        response = client.get("/api/v1/productos/buscar?q=")
        
        assert response.status_code == 422  # Validation error
    
    def test_buscar_productos_with_filters(self, client: TestClient, sample_product):
        """Test búsqueda con filtros"""
        response = client.get(
            "/api/v1/productos/buscar"
            "?q=Test"
            "&precio_min=1000"
            "&precio_max=2000"
            "&limite=10"
        )
        
        TestUtils.assert_response_success(response)
        data = response.json()
        
        assert "filtros_aplicados" in data
        assert data["filtros_aplicados"]["precio_min"] == 1000
        assert data["filtros_aplicados"]["precio_max"] == 2000
    
    def test_buscar_productos_with_location(self, client: TestClient, sample_product):
        """Test búsqueda con geolocalización"""
        response = client.get(
            "/api/v1/productos/buscar"
            "?q=Test"
            "&lat=-33.4489"
            "&lon=-70.6693"
            "&radio_km=10"
        )
        
        TestUtils.assert_response_success(response)
        data = response.json()
        
        assert "filtros_aplicados" in data
        assert data["filtros_aplicados"]["ubicacion"]["lat"] == -33.4489
        assert data["filtros_aplicados"]["ubicacion"]["lon"] == -70.6693
    
    def test_buscar_productos_invalid_coordinates(self, client: TestClient):
        """Test búsqueda con coordenadas inválidas"""
        # Solo latitud sin longitud
        response = client.get("/api/v1/productos/buscar?q=Test&lat=-33.4489")
        
        TestUtils.assert_response_error(response, 400)

    def test_buscar_productos_con_sugerencia(
        self,
        client: TestClient,
        sample_product,
        sample_product_alt,
        sample_price_alt,
    ):
        """Debe sugerir marca alternativa cuando no hay stock"""
        response = client.get(f"/api/v1/productos/buscar?q={sample_product.name}")

        TestUtils.assert_response_success(response)
        data = response.json()
        producto = data["productos"][0]
        assert producto["marca_sugerida"] == "Alternative Brand"
        assert "Alternative Brand" in producto["explicacion"]

    def test_buscar_productos_sin_sugerencia(
        self,
        client: TestClient,
        sample_product,
        sample_price,
        sample_product_alt,
        sample_price_alt,
    ):
        """No debe sugerir marca cuando hay stock disponible"""
        response = client.get(f"/api/v1/productos/buscar?q={sample_product.name}")

        TestUtils.assert_response_success(response)
        data = response.json()
        producto = data["productos"][0]
        assert "marca_sugerida" not in producto
    
    def test_buscar_productos_invalid_price_range(self, client: TestClient):
        """Test búsqueda con rango de precios inválido"""
        response = client.get(
            "/api/v1/productos/buscar"
            "?q=Test"
            "&precio_min=2000"
            "&precio_max=1000"
        )
        
        TestUtils.assert_response_error(response, 400)
    
    def test_obtener_producto_by_id_success(self, client: TestClient, sample_product):
        """Test obtener producto por ID exitoso"""
        response = client.get(f"/api/v1/productos/{sample_product.id}")
        
        TestUtils.assert_response_success(response)
        data = response.json()
        
        assert data["id"] == str(sample_product.id)
        assert data["nombre"] == sample_product.name
        assert data["marca"] == sample_product.brand
    
    def test_obtener_producto_by_id_not_found(self, client: TestClient):
        """Test obtener producto inexistente"""
        fake_uuid = TestUtils.create_test_uuid()
        response = client.get(f"/api/v1/productos/{fake_uuid}")
        
        TestUtils.assert_response_error(response, 404)
    
    def test_obtener_producto_by_id_invalid_uuid(self, client: TestClient):
        """Test obtener producto con UUID inválido"""
        response = client.get("/api/v1/productos/invalid-uuid")
        
        assert response.status_code == 422  # Validation error
    
    def test_obtener_productos_populares(self, client: TestClient, sample_product):
        """Test obtener productos populares"""
        response = client.get("/api/v1/productos/populares/lista?limite=10")
        
        TestUtils.assert_response_success(response)
        data = response.json()
        
        assert "productos" in data
        assert "criterio" in data
        assert "limite" in data
        assert data["criterio"] == "popularidad"
        assert data["limite"] == 10
    
    def test_obtener_productos_con_descuentos(self, client: TestClient, sample_price):
        """Test obtener productos con descuentos"""
        response = client.get(
            "/api/v1/productos/ofertas/descuentos"
            "?min_descuento=15"
            "&limite=20"
        )
        
        TestUtils.assert_response_success(response)
        data = response.json()
        
        assert "productos" in data
        assert "descuento_minimo" in data
        assert "total_ofertas" in data
        assert data["descuento_minimo"] == 15
    
    def test_obtener_productos_con_descuentos_with_location(self, client: TestClient, sample_price):
        """Test obtener productos con descuentos y ubicación"""
        response = client.get(
            "/api/v1/productos/ofertas/descuentos"
            "?min_descuento=10"
            "&lat=-33.4489"
            "&lon=-70.6693"
            "&radio_km=15"
        )
        
        TestUtils.assert_response_success(response)
        data = response.json()
        
        assert "ubicacion" in data
        assert data["ubicacion"]["lat"] == -33.4489
        assert data["ubicacion"]["lon"] == -70.6693
    
    def test_buscar_por_codigo_barras_success(self, client: TestClient, sample_product):
        """Test búsqueda por código de barras exitosa"""
        request_data = {
            "codigo_barras": sample_product.barcode
        }
        
        response = client.post("/api/v1/productos/buscar-por-codigo", json=request_data)
        
        TestUtils.assert_response_success(response)
        data = response.json()
        
        assert data["id"] == str(sample_product.id)
        assert data["codigo_barras"] == sample_product.barcode
    
    def test_buscar_por_codigo_barras_not_found(self, client: TestClient):
        """Test búsqueda por código de barras inexistente"""
        request_data = {
            "codigo_barras": "9999999999999"
        }
        
        response = client.post("/api/v1/productos/buscar-por-codigo", json=request_data)
        
        TestUtils.assert_response_error(response, 404)
    
    def test_buscar_por_codigo_barras_invalid(self, client: TestClient):
        """Test búsqueda por código de barras inválido"""
        request_data = {
            "codigo_barras": "123"  # Muy corto
        }
        
        response = client.post("/api/v1/productos/buscar-por-codigo", json=request_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_obtener_categorias(self, client: TestClient, sample_category):
        """Test obtener categorías"""
        response = client.get("/api/v1/productos/categorias/lista")
        
        TestUtils.assert_response_success(response)
        data = response.json()
        
        assert "categorias" in data
        assert "total" in data
        assert isinstance(data["categorias"], list)
    
    def test_buscar_productos_special_characters(self, client: TestClient):
        """Test búsqueda con caracteres especiales"""
        # Test con caracteres especiales chilenos
        response = client.get("/api/v1/productos/buscar?q=niño")
        
        TestUtils.assert_response_success(response)
        
        # Test con acentos
        response = client.get("/api/v1/productos/buscar?q=café")
        
        TestUtils.assert_response_success(response)
    
    def test_buscar_productos_pagination(self, client: TestClient, sample_product):
        """Test paginación en búsqueda de productos"""
        # Primera página
        response = client.get("/api/v1/productos/buscar?q=Test&limite=5&skip=0")
        
        TestUtils.assert_response_success(response)
        data = response.json()
        
        assert len(data["productos"]) <= 5
        
        # Segunda página
        response = client.get("/api/v1/productos/buscar?q=Test&limite=5&skip=5")
        
        TestUtils.assert_response_success(response)
    
    def test_buscar_productos_performance(self, client: TestClient, sample_product):
        """Test performance de búsqueda"""
        import time
        
        start_time = time.time()
        response = client.get("/api/v1/productos/buscar?q=Test")
        end_time = time.time()
        
        TestUtils.assert_response_success(response)
        
        # Verificar que la respuesta sea rápida (menos de 1 segundo)
        response_time = end_time - start_time
        assert response_time < 1.0
        
        # Verificar que se incluya el tiempo de respuesta
        data = response.json()
        assert "tiempo_respuesta_ms" in data
        assert isinstance(data["tiempo_respuesta_ms"], int)


class TestProductsValidation:
    """Tests de validación para productos"""
    
    def test_search_query_length_validation(self, client: TestClient):
        """Test validación de longitud de query"""
        # Query muy largo
        long_query = "a" * 101
        response = client.get(f"/api/v1/productos/buscar?q={long_query}")
        
        assert response.status_code == 422
    
    def test_price_range_validation(self, client: TestClient):
        """Test validación de rango de precios"""
        # Precio negativo
        response = client.get("/api/v1/productos/buscar?q=Test&precio_min=-100")
        
        assert response.status_code == 422
    
    def test_coordinates_validation(self, client: TestClient):
        """Test validación de coordenadas"""
        # Latitud fuera de rango
        response = client.get("/api/v1/productos/buscar?q=Test&lat=100&lon=-70")
        
        assert response.status_code == 422
        
        # Longitud fuera de rango
        response = client.get("/api/v1/productos/buscar?q=Test&lat=-33&lon=200")
        
        assert response.status_code == 422
    
    def test_limit_validation(self, client: TestClient):
        """Test validación de límites"""
        # Límite muy alto
        response = client.get("/api/v1/productos/buscar?q=Test&limite=1000")
        
        assert response.status_code == 422
        
        # Límite negativo
        response = client.get("/api/v1/productos/buscar?q=Test&limite=-1")
        
        assert response.status_code == 422

