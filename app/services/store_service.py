"""
Servicio de tiendas con búsqueda geográfica y manejo de caracteres especiales
"""
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session

from app.repositories.store_repository import store_repository
from app.core.cache import cache, cache_store_key
from app.core.config import settings


class StoreService:
    """Servicio de tiendas con cache y lógica de negocio"""
    
    def __init__(self):
        self.store_repo = store_repository
        self.cache = cache
    
    def search_by_commune(
        self,
        db: Session,
        termino: str,
        limite: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Búsqueda inteligente por comuna con manejo de caracteres especiales
        Encuentra "Ñuñoa" con cualquier variación: "Nunoa", "nunoa", "NUNOA"
        """
        cache_key = f"stores_commune:{termino.lower()}:{limite}"
        
        # Intentar obtener del cache
        cached_stores = self.cache.get(cache_key)
        if cached_stores:
            return cached_stores
        
        # Buscar en la base de datos
        stores_data = self.store_repo.search_by_commune(db, termino, limite)
        
        # Formatear respuesta
        formatted_stores = []
        for store in stores_data:
            store_info = {
                "id": str(store['id']),
                "nombre": store['name'],
                "supermercado": store['supermarket_name'],
                "tipo_supermercado": store['supermarket_type'],
                "direccion": store['address'],
                "comuna": store['commune'],
                "region": store['region'],
                "telefono": store['phone'],
                "coordenadas": {
                    "latitud": float(store['latitude']) if store['latitude'] else None,
                    "longitud": float(store['longitude']) if store['longitude'] else None
                },
                "horarios": store['opening_hours'],
                "servicios": store['services'] or [],
                "puntuacion_similitud": float(store['similarity_score'])
            }
            formatted_stores.append(store_info)
        
        # Guardar en cache
        self.cache.set(cache_key, formatted_stores, settings.CACHE_TTL_STORES)
        
        return formatted_stores
    
    def get_nearby_stores(
        self,
        db: Session,
        lat: float,
        lon: float,
        radio_km: float = 10.0,
        tipo_supermercado: Optional[str] = None,
        producto_ids: Optional[List[UUID]] = None,
        abierto_ahora: bool = False,
        limite: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Obtener tiendas cercanas con productos disponibles
        """
        cache_key = f"nearby_stores:{lat}:{lon}:{radio_km}:{tipo_supermercado}:{limite}"
        
        # Si se especifican productos, no usar cache (muy específico)
        if not producto_ids:
            cached_stores = self.cache.get(cache_key)
            if cached_stores:
                return cached_stores
        
        # Obtener tiendas cercanas
        if producto_ids:
            stores_data = self.store_repo.get_stores_with_products(
                db, producto_ids, lat, lon, radio_km, limite
            )
        else:
            stores_data = self.store_repo.get_nearby_stores(
                db, lat, lon, radio_km, tipo_supermercado, limite
            )
        
        # Formatear respuesta
        formatted_stores = []
        for store in stores_data:
            store_info = {
                "id": str(store['id']),
                "nombre": store['name'],
                "supermercado": store['supermarket_name'],
                "tipo_supermercado": store['supermarket_type'],
                "direccion": store['address'],
                "comuna": store['commune'],
                "region": store['region'],
                "telefono": store.get('phone'),
                "coordenadas": {
                    "latitud": float(store['latitude']) if store['latitude'] else None,
                    "longitud": float(store['longitude']) if store['longitude'] else None
                },
                "distancia_km": float(store['distance_km']) if 'distance_km' in store else None,
                "tiempo_estimado": int(store['estimated_time_minutes']) if 'estimated_time_minutes' in store else None,
                "horarios": store['opening_hours'],
                "abierto_ahora": True,  # TODO: Implementar lógica real de horarios
                "servicios": self._format_services(store),
                "logo_supermercado": store.get('supermarket_logo')
            }
            
            # Agregar información específica de productos si aplica
            if 'products_available' in store:
                store_info["productos_disponibles"] = int(store['products_available'])
                store_info["precio_promedio"] = float(store['avg_price']) if store['avg_price'] else None
            
            formatted_stores.append(store_info)
        
        # Guardar en cache solo si no se especificaron productos
        if not producto_ids:
            self.cache.set(cache_key, formatted_stores, settings.CACHE_TTL_STORES)
        
        return formatted_stores
    
    def get_store_by_id(
        self,
        db: Session,
        store_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Obtener tienda por ID con información completa
        """
        cache_key = cache_store_key(str(store_id))
        
        # Intentar obtener del cache
        cached_store = self.cache.get(cache_key)
        if cached_store:
            return cached_store
        
        # Obtener de la base de datos
        store = self.store_repo.get_active(db, store_id)
        if not store:
            return None
        
        store_data = {
            "id": str(store.id),
            "nombre": store.name,
            "supermercado": {
                "id": str(store.supermarket.id),
                "nombre": store.supermarket.name,
                "tipo": store.supermarket.type,
                "logo_url": store.supermarket.logo_url,
                "sitio_web": store.supermarket.website_url,
                "compra_minima": float(store.supermarket.minimum_purchase_amount) if store.supermarket.minimum_purchase_amount else None
            },
            "direccion": store.address,
            "comuna": store.commune,
            "region": store.region,
            "telefono": store.phone,
            "email": store.email,
            "coordenadas": {
                "latitud": store.coordinates[0],
                "longitud": store.coordinates[1]
            },
            "horarios": store.opening_hours,
            "servicios": store.get_services_list(),
            "tiene_farmacia": store.has_pharmacy,
            "tiene_panaderia": store.has_bakery,
            "tiene_estacionamiento": store.has_parking,
            "nombre_completo": store.full_name
        }
        
        # Guardar en cache
        self.cache.set(cache_key, store_data, settings.CACHE_TTL_STORES)
        
        return store_data
    
    def calculate_distance(
        self,
        db: Session,
        store_id: UUID,
        lat: float,
        lon: float
    ) -> Optional[float]:
        """
        Calcular distancia entre tienda y ubicación
        """
        return self.store_repo.calculate_distance(db, store_id, lat, lon)
    
    def get_stores_with_services(
        self,
        db: Session,
        servicios: List[str],
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        radio_km: float = 10.0,
        limite: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Obtener tiendas que tienen servicios específicos
        """
        cache_key = f"stores_services:{'_'.join(sorted(servicios))}:{lat}:{lon}:{radio_km}:{limite}"
        
        # Intentar obtener del cache
        cached_stores = self.cache.get(cache_key)
        if cached_stores:
            return cached_stores
        
        stores = self.store_repo.get_stores_with_services(
            db, servicios, lat, lon, radio_km, limite
        )
        
        formatted_stores = []
        for store in stores:
            store_info = {
                "id": str(store.id),
                "nombre": store.name,
                "supermercado": store.supermarket.name,
                "direccion": store.address,
                "comuna": store.commune,
                "coordenadas": {
                    "latitud": store.coordinates[0],
                    "longitud": store.coordinates[1]
                },
                "servicios": store.get_services_list(),
                "servicios_solicitados": [s for s in servicios if s in store.get_services_list()]
            }
            
            # Calcular distancia si se proporcionan coordenadas
            if lat is not None and lon is not None:
                distance = self.calculate_distance(db, store.id, lat, lon)
                if distance:
                    store_info["distancia_km"] = distance
                    store_info["tiempo_estimado"] = int(distance * 2.5)  # Estimación simple
            
            formatted_stores.append(store_info)
        
        # Guardar en cache
        self.cache.set(cache_key, formatted_stores, settings.CACHE_TTL_STORES)
        
        return formatted_stores
    
    def _format_services(self, store_data: Dict[str, Any]) -> List[str]:
        """
        Formatear lista de servicios de una tienda
        """
        services = []
        
        # Servicios booleanos
        if store_data.get('has_pharmacy'):
            services.append("farmacia")
        if store_data.get('has_bakery'):
            services.append("panaderia")
        if store_data.get('has_parking'):
            services.append("estacionamiento")
        
        # Servicios adicionales del campo JSON
        if store_data.get('services') and isinstance(store_data['services'], list):
            services.extend(store_data['services'])
        
        return list(set(services))  # Eliminar duplicados


# Instancia global del servicio
store_service = StoreService()

