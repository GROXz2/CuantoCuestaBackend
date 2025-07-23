"""
Repositorio de tiendas con búsqueda geográfica y manejo de caracteres especiales
"""
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_, text
from geoalchemy2.functions import ST_DWithin, ST_Distance, ST_GeogFromText

from app.models.store import Store
from app.models.supermarket import Supermarket
from app.repositories.base_repository import BaseRepository


class StoreRepository(BaseRepository[Store, dict, dict]):
    """Repositorio de tiendas con funcionalidades geográficas"""
    
    def __init__(self):
        super().__init__(Store)
    
    def search_by_commune(
        self,
        db: Session,
        search_term: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Búsqueda inteligente de tiendas por comuna con manejo de caracteres especiales
        Encuentra "Ñuñoa" con cualquier variación: "Nunoa", "nunoa", "NUNOA"
        """
        query = text("""
            SELECT 
                s.id,
                s.name,
                s.address,
                s.commune,
                s.region,
                s.phone,
                sm.name as supermarket_name,
                sm.type as supermarket_type,
                ST_X(s.location::geometry) as longitude,
                ST_Y(s.location::geometry) as latitude,
                s.opening_hours,
                s.services,
                GREATEST(
                    similarity(s.commune, :search_term),
                    similarity(s.commune_normalized, lower(unaccent(:search_term)))
                ) as similarity_score
            FROM stores.stores s
            JOIN stores.supermarkets sm ON s.supermarket_id = sm.id
            WHERE 
                s.is_active = true
                AND sm.is_active = true
                AND (
                    -- Búsqueda exacta
                    s.commune ILIKE '%' || :search_term || '%'
                    -- Búsqueda normalizada (sin acentos)
                    OR s.commune_normalized ILIKE '%' || lower(unaccent(:search_term)) || '%'
                    -- Búsqueda por similitud
                    OR similarity(s.commune, :search_term) > 0.3
                    OR similarity(s.commune_normalized, lower(unaccent(:search_term))) > 0.3
                )
            ORDER BY similarity_score DESC, s.name
            LIMIT :limit
        """)
        
        result = db.execute(query, {
            'search_term': search_term,
            'limit': limit
        })
        
        return [dict(row) for row in result]
    
    def get_nearby_stores(
        self,
        db: Session,
        latitude: float,
        longitude: float,
        radius_km: float = 10.0,
        supermarket_type: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Obtener tiendas cercanas a una ubicación con cálculo de distancia
        """
        # Crear punto geográfico
        user_location = f"POINT({longitude} {latitude})"
        
        query = text("""
            SELECT 
                s.id,
                s.name,
                s.address,
                s.commune,
                s.region,
                s.phone,
                sm.name as supermarket_name,
                sm.type as supermarket_type,
                sm.logo_url,
                ST_X(s.location::geometry) as longitude,
                ST_Y(s.location::geometry) as latitude,
                s.opening_hours,
                s.services,
                s.has_pharmacy,
                s.has_bakery,
                s.has_parking,
                ROUND(
                    ST_Distance(
                        s.location,
                        ST_GeogFromText(:user_location)
                    ) / 1000, 2
                ) as distance_km,
                ROUND(
                    ST_Distance(
                        s.location,
                        ST_GeogFromText(:user_location)
                    ) / 1000 * 2.5, 0
                ) as estimated_time_minutes
            FROM stores.stores s
            JOIN stores.supermarkets sm ON s.supermarket_id = sm.id
            WHERE 
                s.is_active = true
                AND sm.is_active = true
                AND ST_DWithin(
                    s.location,
                    ST_GeogFromText(:user_location),
                    :radius_meters
                )
                AND (:supermarket_type IS NULL OR sm.type = :supermarket_type)
            ORDER BY distance_km ASC
            LIMIT :limit
        """)
        
        result = db.execute(query, {
            'user_location': user_location,
            'radius_meters': radius_km * 1000,  # Convertir km a metros
            'supermarket_type': supermarket_type,
            'limit': limit
        })
        
        return [dict(row) for row in result]
    
    def get_stores_with_products(
        self,
        db: Session,
        product_ids: List[UUID],
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        radius_km: float = 10.0,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Obtener tiendas que tienen productos específicos disponibles
        """
        product_ids_str = "','".join([str(pid) for pid in product_ids])
        
        base_query = f"""
            SELECT 
                s.id,
                s.name,
                s.address,
                s.commune,
                s.region,
                sm.name as supermarket_name,
                sm.type as supermarket_type,
                ST_X(s.location::geometry) as longitude,
                ST_Y(s.location::geometry) as latitude,
                s.opening_hours,
                s.services,
                COUNT(DISTINCT p.product_id) as products_available,
                ARRAY_AGG(DISTINCT p.product_id) as available_product_ids,
                AVG(p.normal_price) as avg_price
            FROM stores.stores s
            JOIN stores.supermarkets sm ON s.supermarket_id = sm.id
            JOIN pricing.prices p ON s.id = p.store_id
            WHERE 
                s.is_active = true
                AND sm.is_active = true
                AND p.is_active = true
                AND p.stock_status = 'available'
                AND p.product_id IN ('{product_ids_str}')
        """
        
        # Agregar filtro geográfico si se proporcionan coordenadas
        if latitude is not None and longitude is not None:
            user_location = f"POINT({longitude} {latitude})"
            base_query += f"""
                AND ST_DWithin(
                    s.location,
                    ST_GeogFromText('{user_location}'),
                    {radius_km * 1000}
                )
            """
        
        base_query += f"""
            GROUP BY s.id, s.name, s.address, s.commune, s.region, 
                     sm.name, sm.type, s.location, s.opening_hours, s.services
            HAVING COUNT(DISTINCT p.product_id) > 0
        """
        
        # Agregar cálculo de distancia y ordenamiento
        if latitude is not None and longitude is not None:
            user_location = f"POINT({longitude} {latitude})"
            base_query = f"""
                SELECT *,
                    ROUND(
                        ST_Distance(
                            ST_GeogFromText('POINT(' || longitude || ' ' || latitude || ')'),
                            ST_GeogFromText('{user_location}')
                        ) / 1000, 2
                    ) as distance_km
                FROM ({base_query}) subquery
                ORDER BY products_available DESC, distance_km ASC
            """
        else:
            base_query += " ORDER BY products_available DESC, s.name"
        
        base_query += f" LIMIT {limit}"
        
        result = db.execute(text(base_query))
        return [dict(row) for row in result]
    
    def get_by_supermarket(
        self,
        db: Session,
        supermarket_id: UUID,
        commune: Optional[str] = None,
        limit: int = 100
    ) -> List[Store]:
        """Obtener tiendas por supermercado"""
        query = db.query(Store).filter(
            Store.supermarket_id == supermarket_id,
            Store.is_active == True
        )
        
        if commune:
            query = query.filter(
                or_(
                    Store.commune.ilike(f'%{commune}%'),
                    Store.commune_normalized.ilike(f'%{commune.lower()}%')
                )
            )
        
        return query.limit(limit).all()
    
    def calculate_distance(
        self,
        db: Session,
        store_id: UUID,
        latitude: float,
        longitude: float
    ) -> Optional[float]:
        """
        Calcular distancia entre una tienda y una ubicación
        """
        user_location = f"POINT({longitude} {latitude})"
        
        query = text("""
            SELECT ROUND(
                ST_Distance(
                    s.location,
                    ST_GeogFromText(:user_location)
                ) / 1000, 2
            ) as distance_km
            FROM stores.stores s
            WHERE s.id = :store_id
        """)
        
        result = db.execute(query, {
            'store_id': store_id,
            'user_location': user_location
        }).first()
        
        return result.distance_km if result else None
    
    def get_stores_by_region(
        self,
        db: Session,
        region: str,
        limit: int = 100
    ) -> List[Store]:
        """Obtener tiendas por región"""
        return db.query(Store).filter(
            Store.region.ilike(f'%{region}%'),
            Store.is_active == True
        ).limit(limit).all()
    
    def get_stores_with_services(
        self,
        db: Session,
        services: List[str],
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        radius_km: float = 10.0,
        limit: int = 50
    ) -> List[Store]:
        """
        Obtener tiendas que tienen servicios específicos
        """
        query = db.query(Store).filter(Store.is_active == True)
        
        # Filtrar por servicios
        service_conditions = []
        for service in services:
            if service == "farmacia":
                service_conditions.append(Store.has_pharmacy == True)
            elif service == "panaderia":
                service_conditions.append(Store.has_bakery == True)
            elif service == "estacionamiento":
                service_conditions.append(Store.has_parking == True)
            else:
                # Buscar en el campo JSON de servicios
                service_conditions.append(
                    Store.services.contains([service])
                )
        
        if service_conditions:
            query = query.filter(or_(*service_conditions))
        
        # Filtro geográfico si se proporcionan coordenadas
        if latitude is not None and longitude is not None:
            user_location = func.ST_GeogFromText(f"POINT({longitude} {latitude})")
            query = query.filter(
                func.ST_DWithin(Store.location, user_location, radius_km * 1000)
            )
            # Ordenar por distancia
            query = query.order_by(
                func.ST_Distance(Store.location, user_location)
            )
        
        return query.limit(limit).all()


# Instancia global del repositorio
store_repository = StoreRepository()

