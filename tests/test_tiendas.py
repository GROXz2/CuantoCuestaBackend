"""
Tests para endpoints de tiendas con manejo de caracteres especiales
"""
import pytest
from fastapi.testclient import TestClient
from tests.conftest import TestUtils


class TestStoresEndpoints:
    """Tests para endpoints de tiendas"""
    
    def test_buscar_tiendas_por_comuna_success(self, client: TestClient, sample_store):
        """Test búsqueda exitosa por comuna"""
        response = client.get("/api/v1/tiendas/buscar-por-comuna?termino=Ñuñoa")
        
        TestUtils.assert_response_success(response)
        data = response.json()
        
        assert "tiendas" in data
        assert "total" in data
        assert "termino_busqueda" in data
        assert data["termino_busqueda"] == "Ñuñoa"
        assert isinstance(data["tiendas"], list)
    
    def test_buscar_tiendas_caracteres_especiales(self, client: TestClient, sample_store):
        """Test búsqueda con caracteres especiales - funcionalidad clave"""
        # Buscar "Ñuñoa" escribiendo "Nunoa" (sin ñ)
        response = client.get("/api/v1/tiendas/buscar-por-comuna?termino=Nunoa")
        
        TestUtils.assert_response_success(response)
        data = response.json()
        
        assert "tiendas" in data
        assert data["termino_busqueda"] == "Nunoa"
        
        # Buscar en minúsculas
        response = client.get("/api/v1/tiendas/buscar-por-comuna?termino=nunoa")
        
        TestUtils.assert_response_success(response)
        
        # Buscar en mayúsculas
        response = client.get("/api/v1/tiendas/buscar-por-comuna?termino=NUNOA")
        
        TestUtils.assert_response_success(response)
    
    def test_buscar_tiendas_penalolen(self, client: TestClient):
        """Test búsqueda específica para Peñalolén"""
        # Buscar "Peñalolén" escribiendo "Penalolen"
        response = client.get("/api/v1/tiendas/buscar-por-comuna?termino=Penalolen")
        
        TestUtils.assert_response_success(response)
        data = response.json()
        
        assert data["termino_busqueda"] == "Penalolen"
    
    def test_buscar_tiendas_empty_query(self, client: TestClient):
        """Test búsqueda con query vacío"""
        response = client.get("/api/v1/tiendas/buscar-por-comuna?termino=")
        
        assert response.status_code == 422  # Validation error
    
    def test_obtener_tiendas_cercanas_success(self, client: TestClient, sample_store):
        """Test obtener tiendas cercanas exitoso"""
        response = client.get(
            "/api/v1/tiendas/cercanas"
            "?lat=-33.4489"
            "&lon=-70.6693"
            "&radio_km=10"
        )
        
        TestUtils.assert_response_success(response)
        data = response.json()
        
        assert "tiendas" in data
        assert "total" in data
        assert "ubicacion_busqueda" in data
        assert "radio_km" in data
        assert data["ubicacion_busqueda"]["lat"] == -33.4489
        assert data["ubicacion_busqueda"]["lon"] == -70.6693
        assert data["radio_km"] == 10
    
    def test_obtener_tiendas_cercanas_with_filters(self, client: TestClient, sample_store):
        """Test tiendas cercanas con filtros"""
        response = client.get(
            "/api/v1/tiendas/cercanas"
            "?lat=-33.4489"
            "&lon=-70.6693"
            "&radio_km=15"
            "&tipo_supermercado=retail"
            "&abierto_ahora=true"
            "&limite=20"
        )
        
        TestUtils.assert_response_success(response)
        data = response.json()
        
        assert "filtros_aplicados" in data
        assert data["filtros_aplicados"]["tipo_supermercado"] == "retail"
        assert data["filtros_aplicados"]["abierto_ahora"] is True
    
    def test_obtener_tiendas_cercanas_invalid_coordinates(self, client: TestClient):
        """Test tiendas cercanas con coordenadas inválidas"""
        # Latitud fuera de rango
        response = client.get("/api/v1/tiendas/cercanas?lat=100&lon=-70")
        
        assert response.status_code == 422
        
        # Longitud fuera de rango
        response = client.get("/api/v1/tiendas/cercanas?lat=-33&lon=200")
        
        assert response.status_code == 422
    
    def test_obtener_tiendas_cercanas_invalid_supermarket_type(self, client: TestClient):
        """Test tiendas cercanas con tipo de supermercado inválido"""
        response = client.get(
            "/api/v1/tiendas/cercanas"
            "?lat=-33.4489"
            "&lon=-70.6693"
            "&tipo_supermercado=invalid"
        )
        
        TestUtils.assert_response_error(response, 400)
    
    def test_obtener_tienda_by_id_success(self, client: TestClient, sample_store):
        """Test obtener tienda por ID exitoso"""
        response = client.get(f"/api/v1/tiendas/{sample_store.id}")
        
        TestUtils.assert_response_success(response)
        data = response.json()
        
        assert data["id"] == str(sample_store.id)
        assert data["nombre"] == sample_store.name
        assert data["comuna"] == sample_store.commune
        assert "supermercado" in data
        assert "coordenadas" in data
    
    def test_obtener_tienda_by_id_not_found(self, client: TestClient):
        """Test obtener tienda inexistente"""
        fake_uuid = TestUtils.create_test_uuid()
        response = client.get(f"/api/v1/tiendas/{fake_uuid}")
        
        TestUtils.assert_response_error(response, 404)
    
    def test_obtener_tienda_by_id_invalid_uuid(self, client: TestClient):
        """Test obtener tienda con UUID inválido"""
        response = client.get("/api/v1/tiendas/invalid-uuid")
        
        assert response.status_code == 422
    
    def test_obtener_tiendas_con_productos(self, client: TestClient, sample_store, sample_product):
        """Test obtener tiendas con productos específicos"""
        response = client.get(
            f"/api/v1/tiendas/con-productos/disponibles"
            f"?producto_ids={sample_product.id}"
            "&lat=-33.4489"
            "&lon=-70.6693"
            "&radio_km=10"
        )
        
        TestUtils.assert_response_success(response)
        data = response.json()
        
        assert "tiendas" in data
        assert "filtros_aplicados" in data
        assert "productos_solicitados" in data["filtros_aplicados"]
    
    def test_obtener_tiendas_con_productos_multiple(self, client: TestClient, sample_store, sample_product):
        """Test obtener tiendas con múltiples productos"""
        product_id2 = TestUtils.create_test_uuid()
        
        response = client.get(
            f"/api/v1/tiendas/con-productos/disponibles"
            f"?producto_ids={sample_product.id},{product_id2}"
            "&radio_km=15"
        )
        
        TestUtils.assert_response_success(response)
        data = response.json()
        
        assert data["filtros_aplicados"]["productos_solicitados"] == 2
    
    def test_obtener_tiendas_con_productos_invalid_uuids(self, client: TestClient):
        """Test obtener tiendas con UUIDs de productos inválidos"""
        response = client.get(
            "/api/v1/tiendas/con-productos/disponibles"
            "?producto_ids=invalid-uuid,another-invalid"
        )
        
        TestUtils.assert_response_error(response, 400)
    
    def test_buscar_tiendas_con_servicios_success(self, client: TestClient, sample_store):
        """Test buscar tiendas con servicios específicos"""
        response = client.get(
            "/api/v1/tiendas/con-servicios/buscar"
            "?servicios=farmacia,panaderia"
            "&lat=-33.4489"
            "&lon=-70.6693"
            "&radio_km=10"
        )
        
        TestUtils.assert_response_success(response)
        data = response.json()
        
        assert "tiendas" in data
        assert "servicios_solicitados" in data
        assert "farmacia" in data["servicios_solicitados"]
        assert "panaderia" in data["servicios_solicitados"]
    
    def test_buscar_tiendas_con_servicios_single(self, client: TestClient, sample_store):
        """Test buscar tiendas con un solo servicio"""
        response = client.get(
            "/api/v1/tiendas/con-servicios/buscar"
            "?servicios=farmacia"
            "&radio_km=15"
        )
        
        TestUtils.assert_response_success(response)
        data = response.json()
        
        assert data["servicios_solicitados"] == ["farmacia"]
    
    def test_buscar_tiendas_con_servicios_invalid(self, client: TestClient):
        """Test buscar tiendas con servicios inválidos"""
        response = client.get(
            "/api/v1/tiendas/con-servicios/buscar"
            "?servicios=servicio_inexistente"
        )
        
        TestUtils.assert_response_error(response, 400)
    
    def test_obtener_supermercados(self, client: TestClient, sample_supermarket):
        """Test obtener lista de supermercados"""
        response = client.get("/api/v1/tiendas/supermercados/lista")
        
        TestUtils.assert_response_success(response)
        data = response.json()
        
        assert "supermercados" in data
        assert "total" in data
        assert isinstance(data["supermercados"], list)
    
    def test_obtener_supermercados_with_filters(self, client: TestClient, sample_supermarket):
        """Test obtener supermercados con filtros"""
        response = client.get(
            "/api/v1/tiendas/supermercados/lista"
            "?tipo=retail"
            "&activos_solamente=true"
        )
        
        TestUtils.assert_response_success(response)


class TestStoresSpecialFeatures:
    """Tests para funcionalidades especiales de tiendas"""
    
    def test_search_similarity_scoring(self, client: TestClient, sample_store):
        """Test puntuación de similitud en búsqueda"""
        response = client.get("/api/v1/tiendas/buscar-por-comuna?termino=Ñuñoa")
        
        TestUtils.assert_response_success(response)
        data = response.json()
        
        if data["tiendas"]:
            # Verificar que se incluya puntuación de similitud
            tienda = data["tiendas"][0]
            assert "puntuacion_similitud" in tienda
            assert isinstance(tienda["puntuacion_similitud"], (int, float))
    
    def test_distance_calculation(self, client: TestClient, sample_store):
        """Test cálculo de distancia"""
        response = client.get(
            "/api/v1/tiendas/cercanas"
            "?lat=-33.4489"
            "&lon=-70.6693"
            "&radio_km=10"
        )
        
        TestUtils.assert_response_success(response)
        data = response.json()
        
        if data["tiendas"]:
            tienda = data["tiendas"][0]
            if "distancia_km" in tienda:
                assert isinstance(tienda["distancia_km"], (int, float))
                assert tienda["distancia_km"] >= 0
    
    def test_time_estimation(self, client: TestClient, sample_store):
        """Test estimación de tiempo"""
        response = client.get(
            "/api/v1/tiendas/cercanas"
            "?lat=-33.4489"
            "&lon=-70.6693"
            "&radio_km=10"
        )
        
        TestUtils.assert_response_success(response)
        data = response.json()
        
        if data["tiendas"]:
            tienda = data["tiendas"][0]
            if "tiempo_estimado" in tienda:
                assert isinstance(tienda["tiempo_estimado"], int)
                assert tienda["tiempo_estimado"] > 0
    
    def test_opening_hours_format(self, client: TestClient, sample_store):
        """Test formato de horarios"""
        response = client.get(f"/api/v1/tiendas/{sample_store.id}")
        
        TestUtils.assert_response_success(response)
        data = response.json()
        
        assert "horarios" in data
        if data["horarios"]:
            assert isinstance(data["horarios"], dict)
    
    def test_services_list_format(self, client: TestClient, sample_store):
        """Test formato de lista de servicios"""
        response = client.get(f"/api/v1/tiendas/{sample_store.id}")
        
        TestUtils.assert_response_success(response)
        data = response.json()
        
        assert "servicios" in data
        assert isinstance(data["servicios"], list)
        
        # Verificar servicios booleanos
        assert "tiene_farmacia" in data
        assert "tiene_panaderia" in data
        assert "tiene_estacionamiento" in data
        assert isinstance(data["tiene_farmacia"], bool)


class TestStoresValidation:
    """Tests de validación para tiendas"""
    
    def test_search_term_length_validation(self, client: TestClient):
        """Test validación de longitud de término de búsqueda"""
        # Término muy largo
        long_term = "a" * 101
        response = client.get(f"/api/v1/tiendas/buscar-por-comuna?termino={long_term}")
        
        assert response.status_code == 422
    
    def test_radius_validation(self, client: TestClient):
        """Test validación de radio de búsqueda"""
        # Radio muy grande
        response = client.get(
            "/api/v1/tiendas/cercanas"
            "?lat=-33.4489"
            "&lon=-70.6693"
            "&radio_km=100"
        )
        
        assert response.status_code == 422
        
        # Radio negativo
        response = client.get(
            "/api/v1/tiendas/cercanas"
            "?lat=-33.4489"
            "&lon=-70.6693"
            "&radio_km=-5"
        )
        
        assert response.status_code == 422
    
    def test_limit_validation(self, client: TestClient):
        """Test validación de límites"""
        # Límite muy alto
        response = client.get(
            "/api/v1/tiendas/buscar-por-comuna"
            "?termino=Test"
            "&limite=1000"
        )
        
        assert response.status_code == 422
    
    def test_services_validation(self, client: TestClient):
        """Test validación de servicios"""
        # Servicios válidos
        valid_services = ["farmacia", "panaderia", "estacionamiento"]
        services_param = ",".join(valid_services)
        
        response = client.get(
            f"/api/v1/tiendas/con-servicios/buscar?servicios={services_param}"
        )
        
        TestUtils.assert_response_success(response)


class TestStoresPerformance:
    """Tests de performance para tiendas"""
    
    def test_search_performance(self, client: TestClient, sample_store):
        """Test performance de búsqueda por comuna"""
        import time
        
        start_time = time.time()
        response = client.get("/api/v1/tiendas/buscar-por-comuna?termino=Ñuñoa")
        end_time = time.time()
        
        TestUtils.assert_response_success(response)
        
        # Verificar que la respuesta sea rápida
        response_time = end_time - start_time
        assert response_time < 1.0
        
        # Verificar tiempo de respuesta en la respuesta
        data = response.json()
        assert "tiempo_respuesta_ms" in data
    
    def test_nearby_stores_performance(self, client: TestClient, sample_store):
        """Test performance de búsqueda geográfica"""
        import time
        
        start_time = time.time()
        response = client.get(
            "/api/v1/tiendas/cercanas"
            "?lat=-33.4489"
            "&lon=-70.6693"
            "&radio_km=10"
        )
        end_time = time.time()
        
        TestUtils.assert_response_success(response)
        
        # Verificar performance
        response_time = end_time - start_time
        assert response_time < 2.0  # Búsqueda geográfica puede ser un poco más lenta

