"""
Servicio de productos con lógica de negocio
"""
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.repositories.product_repository import product_repository
from app.repositories.price_repository import price_repository
from app.core.cache import cache, cache_product_key, cache_search_key
from app.core.config import settings
from app.utils.sanitizer import sanitize_text


class ProductService:
    """Servicio de productos con cache y lógica de negocio"""
    
    def __init__(self):
        self.product_repo = product_repository
        self.price_repo = price_repository
        self.cache = cache
    
    def search_products(
        self,
        db: Session,
        search_term: str,
        category_id: Optional[UUID] = None,
        precio_min: Optional[float] = None,
        precio_max: Optional[float] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        radio_km: float = 10.0,
        limite: int = 50,
        skip: int = 0
    ) -> Dict[str, Any]:
        """
        Búsqueda inteligente de productos con cache
        """
        search_term = sanitize_text(search_term)
        if not search_term:
            raise HTTPException(status_code=422, detail="search_term")

        # Generar clave de cache
        filters = {
            'category_id': str(category_id) if category_id else None,
            'precio_min': precio_min,
            'precio_max': precio_max,
            'lat': lat,
            'lon': lon,
            'radio_km': radio_km,
            'limite': limite,
            'skip': skip
        }
        cache_key = cache_search_key(search_term, filters)
        
        # Intentar obtener del cache
        cached_result = self.cache.get(cache_key)
        if cached_result:
            return cached_result
        
        # Buscar productos
        try:
            products = self.product_repo.search_products(
                db, search_term, category_id, limite, skip
            )
        except ValueError:
            raise HTTPException(status_code=422, detail="search_term")
        
        # Enriquecer con información de precios
        enriched_products = []
        for product in products:
            product_data = {
                "id": str(product.id),
                "nombre": product.name,
                "marca": product.brand,
                "categoria": product.category.name if product.category else None,
                "codigo_barras": product.barcode,
                "tipo_unidad": product.unit_type,
                "tamaño_unidad": product.unit_size,
                "imagen_url": product.image_url,
                "descripcion": product.description
            }
            
            # Obtener mejor precio si se proporcionan coordenadas
            if lat is not None and lon is not None:
                best_price = self.price_repo.get_best_price_for_product(
                    db, product.id, lat, lon, radio_km
                )
                if best_price:
                    product_data.update({
                        "precio_mejor": float(best_price['discount_price'] or best_price['normal_price']),
                        "precio_normal": float(best_price['normal_price']),
                        "tiene_descuento": bool(best_price['discount_price']),
                        "porcentaje_descuento": float(best_price['discount_percentage'] or 0),
                        "tienda_mejor_precio": best_price['store_name']
                    })
            
            # Contar tiendas disponibles
            available_stores = len(self.price_repo.get_current_prices_for_product(
                db, product.id, lat, lon, radio_km
            ))
            product_data["tiendas_disponibles"] = available_stores
            
            enriched_products.append(product_data)
        
        # Filtrar por rango de precios si se especifica
        if precio_min is not None or precio_max is not None:
            filtered_products = []
            for product in enriched_products:
                price = product.get("precio_mejor")
                if price is not None:
                    if precio_min is not None and price < precio_min:
                        continue
                    if precio_max is not None and price > precio_max:
                        continue
                filtered_products.append(product)
            enriched_products = filtered_products
        
        result = {
            "productos": enriched_products,
            "total": len(enriched_products),
            "termino_busqueda": search_term,
            "filtros_aplicados": {
                "categoria_id": str(category_id) if category_id else None,
                "precio_min": precio_min,
                "precio_max": precio_max,
                "ubicacion": {"lat": lat, "lon": lon} if lat and lon else None,
                "radio_km": radio_km
            }
        }
        
        # Guardar en cache
        self.cache.set(cache_key, result, settings.CACHE_TTL_PRODUCTS)
        
        return result
    
    def get_product_by_id(
        self,
        db: Session,
        product_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Obtener producto por ID con cache
        """
        cache_key = cache_product_key(str(product_id))
        
        # Intentar obtener del cache
        cached_product = self.cache.get(cache_key)
        if cached_product:
            return cached_product
        
        # Obtener de la base de datos
        product = self.product_repo.get_active(db, product_id)
        if not product:
            return None
        
        product_data = {
            "id": str(product.id),
            "nombre": product.name,
            "marca": product.brand,
            "categoria": {
                "id": str(product.category.id),
                "nombre": product.category.name,
                "slug": product.category.slug
            } if product.category else None,
            "codigo_barras": product.barcode,
            "descripcion": product.description,
            "tipo_unidad": product.unit_type,
            "tamaño_unidad": product.unit_size,
            "imagen_url": product.image_url,
            "nombre_completo": product.full_name,
            "unidad_display": product.display_unit
        }
        
        # Guardar en cache
        self.cache.set(cache_key, product_data, settings.CACHE_TTL_PRODUCTS)
        
        return product_data
    
    def get_popular_products(
        self,
        db: Session,
        limite: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Obtener productos populares
        """
        cache_key = f"popular_products:{limite}"
        
        # Intentar obtener del cache
        cached_products = self.cache.get(cache_key)
        if cached_products:
            return cached_products
        
        products = self.product_repo.get_popular_products(db, limite)
        
        popular_products = []
        for product in products:
            product_data = {
                "id": str(product.id),
                "nombre": product.name,
                "marca": product.brand,
                "categoria": product.category.name if product.category else None,
                "imagen_url": product.image_url,
                "nombre_completo": product.full_name
            }
            popular_products.append(product_data)
        
        # Guardar en cache por más tiempo (productos populares cambian menos)
        self.cache.set(cache_key, popular_products, settings.CACHE_TTL_PRODUCTS * 2)
        
        return popular_products
    
    def get_products_with_discounts(
        self,
        db: Session,
        min_descuento: float = 10.0,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        radio_km: float = 10.0,
        limite: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Obtener productos con descuentos significativos
        """
        cache_key = f"discounted_products:{min_descuento}:{lat}:{lon}:{radio_km}:{limite}"
        
        # Intentar obtener del cache
        cached_products = self.cache.get(cache_key)
        if cached_products:
            return cached_products
        
        discounted_prices = self.price_repo.get_products_with_best_discounts(
            db, min_descuento, lat, lon, radio_km, limite
        )
        
        products_with_discounts = []
        for price_data in discounted_prices:
            product_info = {
                "id": str(price_data['product_id']),
                "nombre": price_data['product_name'],
                "marca": price_data['product_brand'],
                "precio_normal": float(price_data['normal_price']),
                "precio_descuento": float(price_data['discount_price']),
                "porcentaje_descuento": float(price_data['discount_percentage']),
                "ahorro": float(price_data['normal_price'] - price_data['discount_price']),
                "tienda": {
                    "nombre": price_data['store_name'],
                    "comuna": price_data['store_commune'],
                    "supermercado": price_data['supermarket_name'],
                    "logo_url": price_data['supermarket_logo']
                },
                "descripcion_promocion": price_data['promotion_description']
            }
            
            if lat is not None and lon is not None and 'distance_km' in price_data:
                product_info["distancia_km"] = float(price_data['distance_km'])
            
            products_with_discounts.append(product_info)
        
        # Cache por menos tiempo (ofertas cambian frecuentemente)
        self.cache.set(cache_key, products_with_discounts, settings.CACHE_TTL_PRICES)
        
        return products_with_discounts
    
    def get_product_by_barcode(
        self,
        db: Session,
        barcode: str
    ) -> Optional[Dict[str, Any]]:
        """
        Obtener producto por código de barras
        """
        cache_key = f"product_barcode:{barcode}"
        
        # Intentar obtener del cache
        cached_product = self.cache.get(cache_key)
        if cached_product:
            return cached_product
        
        product = self.product_repo.get_by_barcode(db, barcode)
        if not product:
            return None
        
        product_data = self.get_product_by_id(db, product.id)
        
        # Guardar en cache
        self.cache.set(cache_key, product_data, settings.CACHE_TTL_PRODUCTS)
        
        return product_data


# Instancia global del servicio
product_service = ProductService()

