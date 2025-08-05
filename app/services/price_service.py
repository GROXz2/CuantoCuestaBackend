"""Servicio de precios con comparación y análisis"""
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta
import json
import logging

from sqlalchemy.orm import Session

from app.repositories.price_repository import price_repository
from app.services.product_service import product_service
from app.services.store_service import store_service
from app.core.cache import cache, cache_price_key
from app.core.config import settings
from openai_client import consulta_gpt

logger = logging.getLogger(__name__)


class PriceService:
    """Servicio de precios con cache y lógica de negocio"""
    
    def __init__(self):
        self.price_repo = price_repository
        self.product_service = product_service
        self.store_service = store_service
        self.cache = cache

    def needs_rescrape(self, db: Session, product_id: UUID) -> bool:
        """Verifica si un producto requiere re-scraping y lo ejecuta si es necesario."""
        prices = self.price_repo.get_current_prices_for_product(db, product_id)
        latest_scraped = None
        if prices:
            scraped_dates = [p.get("scraped_at") for p in prices if p.get("scraped_at")]
            if scraped_dates:
                latest_scraped = max(scraped_dates)

        if latest_scraped and datetime.utcnow() - latest_scraped < timedelta(hours=24):
            logger.info("Producto %s actualizado recientemente (%s)", product_id, latest_scraped)
            return False

        logger.info("Re-scrape necesario para producto %s", product_id)
        try:
            prompt = (
                "Devuelve un JSON con los campos store_id, normal_price, discount_price, "
                "discount_percentage, stock_status y promotion_description para el producto "
                f"{product_id}"
            )
            gpt_response = consulta_gpt(prompt)
            logger.debug("Respuesta de GPT para %s: %s", product_id, gpt_response)
            data = json.loads(gpt_response)
        except Exception as exc:
            logger.error("Error al obtener datos desde GPT para %s: %s", product_id, exc)
            return False

        try:
            price_data = {
                "product_id": product_id,
                "store_id": data.get("store_id"),
                "normal_price": data.get("normal_price"),
                "discount_price": data.get("discount_price"),
                "discount_percentage": data.get("discount_percentage"),
                "stock_status": data.get("stock_status", "available"),
                "promotion_description": data.get("promotion_description"),
                "scraped_at": datetime.utcnow(),
            }
            self.price_repo.create(db, obj_in=price_data)
            logger.info("Precio actualizado y persistido para producto %s", product_id)
            return True
        except Exception as exc:
            logger.error(
                "Error al persistir datos de precio para %s: %s", product_id, exc
            )
            return False
    
    def compare_prices(
        self,
        db: Session,
        product_id: UUID,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        radio_km: float = 10.0,
        incluir_mayoristas: bool = False
    ) -> Dict[str, Any]:
        """
        Comparar precios de un producto entre diferentes tiendas
        """
        cache_key = f"price_comparison:{product_id}:{lat}:{lon}:{radio_km}:{incluir_mayoristas}"
        
        # Intentar obtener del cache
        cached_comparison = self.cache.get(cache_key)
        if cached_comparison:
            return cached_comparison
        
        # Obtener información del producto
        product_info = self.product_service.get_product_by_id(db, product_id)
        if not product_info:
            return {
                "error": "Producto no encontrado",
                "product_id": str(product_id)
            }
        
        # Obtener comparación de precios
        comparison_data = self.price_repo.get_price_comparison(
            db, product_id, lat, lon, radio_km, incluir_mayoristas
        )
        
        # Formatear respuesta
        formatted_prices = []
        for price_data in comparison_data["prices"]:
            price_info = {
                "tienda_id": str(price_data['store_id']),
                "supermercado": price_data['supermarket_name'],
                "tienda_nombre": price_data['store_name'],
                "comuna": price_data['store_commune'],
                "direccion": price_data['store_address'],
                "telefono": price_data['store_phone'],
                "precio_normal": float(price_data['normal_price']),
                "precio_descuento": float(price_data['discount_price']) if price_data['discount_price'] else None,
                "porcentaje_descuento": float(price_data['discount_percentage']) if price_data['discount_percentage'] else 0,
                "precio_efectivo": float(price_data['discount_price'] or price_data['normal_price']),
                "stock_disponible": price_data['stock_status'] == 'available',
                "estado_stock": price_data['stock_status'],
                "descripcion_promocion": price_data['promotion_description'],
                "fecha_actualizacion": price_data['scraped_at'].isoformat() if price_data['scraped_at'] else None,
                "logo_supermercado": price_data['supermarket_logo']
            }
            
            # Agregar información geográfica si está disponible
            if 'distance_km' in price_data and price_data['distance_km'] is not None:
                price_info.update({
                    "distancia_km": float(price_data['distance_km']),
                    "tiempo_estimado_min": int(price_data['estimated_time_minutes']) if price_data['estimated_time_minutes'] else None
                })
            
            formatted_prices.append(price_info)
        
        # Generar recomendación inteligente
        recommendation = self._generate_recommendation(
            comparison_data["statistics"],
            formatted_prices,
            lat is not None and lon is not None
        )
        
        result = {
            "producto": {
                "id": str(product_id),
                "nombre": product_info["nombre"],
                "marca": product_info["marca"],
                "categoria": product_info["categoria"]["nombre"] if product_info["categoria"] else None,
                "nombre_completo": product_info["nombre_completo"]
            },
            "precios": formatted_prices,
            "estadisticas": {
                "total_tiendas": comparison_data["statistics"]["total_stores"],
                "precio_minimo": comparison_data["statistics"]["min_price"],
                "precio_maximo": comparison_data["statistics"]["max_price"],
                "precio_promedio": round(comparison_data["statistics"]["avg_price"], 0),
                "ahorro_maximo": comparison_data["statistics"]["max_savings"],
                "ofertas_con_descuento": comparison_data["statistics"]["discounted_offers"]
            },
            "recomendacion": recommendation,
            "filtros_aplicados": {
                "ubicacion": {"lat": lat, "lon": lon} if lat and lon else None,
                "radio_km": radio_km,
                "incluir_mayoristas": incluir_mayoristas
            }
        }
        
        # Guardar en cache
        self.cache.set(cache_key, result, settings.CACHE_TTL_PRICES)
        
        return result
    
    def get_best_deals(
        self,
        db: Session,
        min_descuento: float = 20.0,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        radio_km: float = 10.0,
        limite: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Obtener las mejores ofertas disponibles
        """
        cache_key = f"best_deals:{min_descuento}:{lat}:{lon}:{radio_km}:{limite}"
        
        # Intentar obtener del cache
        cached_deals = self.cache.get(cache_key)
        if cached_deals:
            return cached_deals
        
        # Obtener ofertas de la base de datos
        deals_data = self.price_repo.get_products_with_best_discounts(
            db, min_descuento, lat, lon, radio_km, limite
        )
        
        # Formatear respuesta
        formatted_deals = []
        for deal in deals_data:
            deal_info = {
                "producto": {
                    "id": str(deal['product_id']),
                    "nombre": deal['product_name'],
                    "marca": deal['product_brand']
                },
                "precio_normal": float(deal['normal_price']),
                "precio_descuento": float(deal['discount_price']),
                "porcentaje_descuento": float(deal['discount_percentage']),
                "ahorro": float(deal['normal_price'] - deal['discount_price']),
                "tienda": {
                    "id": str(deal['store_id']),
                    "nombre": deal['store_name'],
                    "comuna": deal['store_commune'],
                    "supermercado": deal['supermarket_name'],
                    "logo_url": deal['supermarket_logo']
                },
                "descripcion_promocion": deal['promotion_description']
            }
            
            # Agregar distancia si está disponible
            if 'distance_km' in deal and deal['distance_km'] is not None:
                deal_info["distancia_km"] = float(deal['distance_km'])
                deal_info["tiempo_estimado_min"] = int(deal['distance_km'] * 2.5)
            
            formatted_deals.append(deal_info)
        
        # Guardar en cache
        self.cache.set(cache_key, formatted_deals, settings.CACHE_TTL_PRICES)
        
        return formatted_deals
    
    def get_price_history(
        self,
        db: Session,
        product_id: UUID,
        store_id: UUID,
        dias: int = 30
    ) -> Dict[str, Any]:
        """
        Obtener historial de precios de un producto en una tienda
        """
        cache_key = f"price_history:{product_id}:{store_id}:{dias}"
        
        # Intentar obtener del cache
        cached_history = self.cache.get(cache_key)
        if cached_history:
            return cached_history
        
        # Obtener información del producto y tienda
        product_info = self.product_service.get_product_by_id(db, product_id)
        store_info = self.store_service.get_store_by_id(db, store_id)
        
        if not product_info or not store_info:
            return {
                "error": "Producto o tienda no encontrados",
                "product_id": str(product_id),
                "store_id": str(store_id)
            }
        
        # Obtener historial
        history_data = self.price_repo.get_price_history(db, product_id, store_id, dias)
        
        # Formatear historial
        formatted_history = []
        for entry in history_data:
            history_entry = {
                "fecha": entry['price_date'].isoformat(),
                "precio_normal": float(entry['normal_price']),
                "precio_descuento": float(entry['discount_price']) if entry['discount_price'] else None,
                "porcentaje_descuento": float(entry['discount_percentage']) if entry['discount_percentage'] else 0,
                "precio_efectivo": float(entry['discount_price'] or entry['normal_price']),
                "estado_stock": entry['stock_status'],
                "fecha_hora_actualizacion": entry['scraped_at'].isoformat()
            }
            formatted_history.append(history_entry)
        
        # Calcular estadísticas del historial
        if formatted_history:
            effective_prices = [h['precio_efectivo'] for h in formatted_history]
            statistics = {
                "precio_minimo_periodo": min(effective_prices),
                "precio_maximo_periodo": max(effective_prices),
                "precio_promedio_periodo": round(sum(effective_prices) / len(effective_prices), 0),
                "variacion_precio": max(effective_prices) - min(effective_prices),
                "total_registros": len(formatted_history),
                "dias_con_descuento": len([h for h in formatted_history if h['precio_descuento']]),
                "descuento_promedio": round(
                    sum([h['porcentaje_descuento'] for h in formatted_history if h['porcentaje_descuento'] > 0]) /
                    max(1, len([h for h in formatted_history if h['porcentaje_descuento'] > 0])), 1
                )
            }
        else:
            statistics = {}
        
        result = {
            "producto": product_info,
            "tienda": store_info,
            "historial": formatted_history,
            "estadisticas": statistics,
            "periodo_dias": dias
        }
        
        # Guardar en cache por más tiempo (historial cambia menos)
        self.cache.set(cache_key, result, settings.CACHE_TTL_PRICES * 2)
        
        return result
    
    def _generate_recommendation(
        self,
        statistics: Dict[str, Any],
        prices: List[Dict[str, Any]],
        has_location: bool
    ) -> str:
        """
        Generar recomendación inteligente basada en precios y ubicación
        """
        if not prices:
            return "No se encontraron precios disponibles para este producto."
        
        # Encontrar mejor precio
        best_price = min(prices, key=lambda x: x['precio_efectivo'])
        
        # Calcular ahorro vs precio más caro
        max_price = max(prices, key=lambda x: x['precio_efectivo'])['precio_efectivo']
        savings = max_price - best_price['precio_efectivo']
        
        # Generar recomendación contextual
        recommendation = f"Mejor precio en {best_price['tienda_nombre']} "
        
        if best_price['precio_descuento']:
            recommendation += f"con {best_price['porcentaje_descuento']:.1f}% descuento "
        
        recommendation += f"a ${best_price['precio_efectivo']:,.0f}".replace(",", ".")
        
        if savings > 0:
            percentage_savings = (savings / max_price) * 100
            recommendation += f", ahorrando ${savings:,.0f}".replace(",", ".") 
            recommendation += f" ({percentage_savings:.1f}%) vs el más caro"
        
        # Agregar información de distancia si está disponible
        if has_location and 'distancia_km' in best_price:
            recommendation += f". Ubicado a {best_price['distancia_km']} km"
            if best_price.get('tiempo_estimado_min'):
                recommendation += f" ({best_price['tiempo_estimado_min']} min aprox.)"
        
        return recommendation


# Instancia global del servicio
price_service = PriceService()

