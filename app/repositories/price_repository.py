"""
Repositorio de precios con comparación y análisis
"""
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, text, desc
from decimal import Decimal

from app.models.price import Price
from app.models.product import Product
from app.models.store import Store
from app.models.supermarket import Supermarket
from app.repositories.base_repository import BaseRepository


class PriceRepository(BaseRepository[Price, dict, dict]):
    """Repositorio de precios con funcionalidades de comparación"""
    
    def __init__(self):
        super().__init__(Price)
    
    def get_current_prices_for_product(
        self,
        db: Session,
        product_id: UUID,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        radius_km: float = 10.0,
        include_mayoristas: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Obtener precios actuales de un producto en diferentes tiendas
        """
        # Subconsulta para obtener el precio más reciente por tienda
        latest_prices = db.query(
            Price.store_id,
            func.max(Price.scraped_at).label('latest_scraped_at')
        ).filter(
            Price.product_id == product_id,
            Price.is_active == True
        ).group_by(Price.store_id).subquery()
        
        # Query principal con joins
        base_query = """
            SELECT 
                p.id as price_id,
                p.product_id,
                p.store_id,
                p.normal_price,
                p.discount_price,
                p.discount_percentage,
                p.stock_status,
                p.promotion_description,
                p.promotion_valid_until,
                p.scraped_at,
                s.name as store_name,
                s.address as store_address,
                s.commune as store_commune,
                s.phone as store_phone,
                sm.name as supermarket_name,
                sm.type as supermarket_type,
                sm.logo_url as supermarket_logo,
                ST_X(s.location::geometry) as longitude,
                ST_Y(s.location::geometry) as latitude
        """
        
        # Agregar cálculo de distancia si se proporcionan coordenadas
        if latitude is not None and longitude is not None:
            user_location = f"POINT({longitude} {latitude})"
            base_query += f""",
                ROUND(
                    ST_Distance(
                        s.location,
                        ST_GeogFromText('{user_location}')
                    ) / 1000, 2
                ) as distance_km,
                ROUND(
                    ST_Distance(
                        s.location,
                        ST_GeogFromText('{user_location}')
                    ) / 1000 * 2.5, 0
                ) as estimated_time_minutes
            """
        
        base_query += """
            FROM pricing.prices p
            JOIN stores.stores s ON p.store_id = s.id
            JOIN stores.supermarkets sm ON s.supermarket_id = sm.id
            WHERE 
                p.product_id = :product_id
                AND p.is_active = true
                AND s.is_active = true
                AND sm.is_active = true
                AND p.stock_status = 'available'
                AND (p.store_id, p.scraped_at) IN (
                    SELECT store_id, MAX(scraped_at)
                    FROM pricing.prices
                    WHERE product_id = :product_id AND is_active = true
                    GROUP BY store_id
                )
        """
        
        # Filtrar por tipo de supermercado
        if not include_mayoristas:
            base_query += " AND sm.type = 'retail'"
        
        # Filtro geográfico
        if latitude is not None and longitude is not None:
            base_query += f"""
                AND ST_DWithin(
                    s.location,
                    ST_GeogFromText('{user_location}'),
                    {radius_km * 1000}
                )
            """
        
        # Ordenamiento
        if latitude is not None and longitude is not None:
            base_query += " ORDER BY distance_km ASC, p.normal_price ASC"
        else:
            base_query += " ORDER BY p.normal_price ASC"
        
        result = db.execute(text(base_query), {'product_id': product_id})
        return [dict(row) for row in result]
    
    def get_best_price_for_product(
        self,
        db: Session,
        product_id: UUID,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        radius_km: float = 10.0
    ) -> Optional[Dict[str, Any]]:
        """
        Obtener el mejor precio para un producto
        """
        prices = self.get_current_prices_for_product(
            db, product_id, latitude, longitude, radius_km
        )
        
        if not prices:
            return None
        
        # Encontrar el mejor precio (considerando descuentos)
        best_price = min(prices, key=lambda x: x['discount_price'] or x['normal_price'])
        return best_price
    
    def get_price_comparison(
        self,
        db: Session,
        product_id: UUID,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        radius_km: float = 10.0,
        include_mayoristas: bool = False
    ) -> Dict[str, Any]:
        """
        Obtener comparación completa de precios para un producto
        """
        prices = self.get_current_prices_for_product(
            db, product_id, latitude, longitude, radius_km, include_mayoristas
        )
        
        if not prices:
            return {
                "product_id": product_id,
                "prices": [],
                "statistics": {},
                "recommendations": {}
            }
        
        # Calcular estadísticas
        effective_prices = [p['discount_price'] or p['normal_price'] for p in prices]
        normal_prices = [p['normal_price'] for p in prices]
        
        min_price = min(effective_prices)
        max_price = max(effective_prices)
        avg_price = sum(effective_prices) / len(effective_prices)
        
        # Encontrar mejor oferta
        best_deal = min(prices, key=lambda x: x['discount_price'] or x['normal_price'])
        
        # Calcular ahorros
        max_savings = max_price - min_price
        
        # Contar ofertas con descuento
        discounted_offers = len([p for p in prices if p['discount_price']])
        
        return {
            "product_id": product_id,
            "prices": prices,
            "statistics": {
                "total_stores": len(prices),
                "min_price": float(min_price),
                "max_price": float(max_price),
                "avg_price": float(avg_price),
                "max_savings": float(max_savings),
                "discounted_offers": discounted_offers
            },
            "recommendations": {
                "best_price_store": best_deal['store_name'],
                "best_price": float(best_deal['discount_price'] or best_deal['normal_price']),
                "savings_vs_most_expensive": float(max_price - (best_deal['discount_price'] or best_deal['normal_price'])),
                "has_discount": bool(best_deal['discount_price']),
                "discount_percentage": float(best_deal['discount_percentage'] or 0)
            }
        }
    
    def get_price_history(
        self,
        db: Session,
        product_id: UUID,
        store_id: UUID,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Obtener historial de precios de un producto en una tienda
        """
        start_date = datetime.now() - timedelta(days=days)
        
        query = text("""
            SELECT 
                p.normal_price,
                p.discount_price,
                p.discount_percentage,
                p.stock_status,
                p.scraped_at,
                DATE(p.scraped_at) as price_date
            FROM pricing.prices p
            WHERE 
                p.product_id = :product_id
                AND p.store_id = :store_id
                AND p.scraped_at >= :start_date
                AND p.is_active = true
            ORDER BY p.scraped_at DESC
        """)
        
        result = db.execute(query, {
            'product_id': product_id,
            'store_id': store_id,
            'start_date': start_date
        })
        
        return [dict(row) for row in result]
    
    def get_products_with_best_discounts(
        self,
        db: Session,
        min_discount_percentage: float = 20.0,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        radius_km: float = 10.0,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Obtener productos con los mejores descuentos
        """
        base_query = """
            SELECT 
                p.id as price_id,
                p.product_id,
                p.store_id,
                p.normal_price,
                p.discount_price,
                p.discount_percentage,
                p.promotion_description,
                prod.name as product_name,
                prod.brand as product_brand,
                s.name as store_name,
                s.commune as store_commune,
                sm.name as supermarket_name,
                sm.logo_url as supermarket_logo
        """
        
        if latitude is not None and longitude is not None:
            user_location = f"POINT({longitude} {latitude})"
            base_query += f""",
                ROUND(
                    ST_Distance(
                        s.location,
                        ST_GeogFromText('{user_location}')
                    ) / 1000, 2
                ) as distance_km
            """
        
        base_query += """
            FROM pricing.prices p
            JOIN products.products prod ON p.product_id = prod.id
            JOIN stores.stores s ON p.store_id = s.id
            JOIN stores.supermarkets sm ON s.supermarket_id = sm.id
            WHERE 
                p.is_active = true
                AND prod.is_active = true
                AND s.is_active = true
                AND sm.is_active = true
                AND p.discount_percentage >= :min_discount
                AND p.stock_status = 'available'
                AND (p.store_id, p.product_id, p.scraped_at) IN (
                    SELECT store_id, product_id, MAX(scraped_at)
                    FROM pricing.prices
                    WHERE is_active = true
                    GROUP BY store_id, product_id
                )
        """
        
        if latitude is not None and longitude is not None:
            base_query += f"""
                AND ST_DWithin(
                    s.location,
                    ST_GeogFromText('{user_location}'),
                    {radius_km * 1000}
                )
                ORDER BY p.discount_percentage DESC, distance_km ASC
            """
        else:
            base_query += " ORDER BY p.discount_percentage DESC"
        
        base_query += f" LIMIT {limit}"
        
        result = db.execute(text(base_query), {
            'min_discount': min_discount_percentage
        })
        
        return [dict(row) for row in result]
    
    def get_average_price_by_commune(
        self,
        db: Session,
        product_id: UUID
    ) -> List[Dict[str, Any]]:
        """
        Obtener precio promedio por comuna para un producto
        """
        query = text("""
            SELECT 
                s.commune,
                COUNT(*) as store_count,
                ROUND(AVG(p.normal_price), 0) as avg_normal_price,
                ROUND(AVG(COALESCE(p.discount_price, p.normal_price)), 0) as avg_effective_price,
                ROUND(MIN(COALESCE(p.discount_price, p.normal_price)), 0) as min_price,
                ROUND(MAX(COALESCE(p.discount_price, p.normal_price)), 0) as max_price
            FROM pricing.prices p
            JOIN stores.stores s ON p.store_id = s.id
            WHERE 
                p.product_id = :product_id
                AND p.is_active = true
                AND s.is_active = true
                AND p.stock_status = 'available'
                AND (p.store_id, p.scraped_at) IN (
                    SELECT store_id, MAX(scraped_at)
                    FROM pricing.prices
                    WHERE product_id = :product_id AND is_active = true
                    GROUP BY store_id
                )
            GROUP BY s.commune
            HAVING COUNT(*) >= 2
            ORDER BY avg_effective_price ASC
        """)
        
        result = db.execute(query, {'product_id': product_id})
        return [dict(row) for row in result]


# Instancia global del repositorio
price_repository = PriceRepository()

