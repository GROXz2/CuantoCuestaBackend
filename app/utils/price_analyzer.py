"""
Utilidad de Análisis de Precios
===============================

Esta utilidad proporciona funciones para analizar precios, detectar ofertas,
y realizar comparaciones inteligentes entre productos y tiendas.

Autor: Manus AI
Fecha: 2024
"""

from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import statistics
import logging

logger = logging.getLogger(__name__)


@dataclass
class ProductPrice:
    """Información de precio de un producto"""
    product_id: str
    product_name: str
    store_id: str
    store_name: str
    price: float
    original_price: Optional[float] = None  # Precio antes de descuento
    discount_percentage: Optional[float] = None
    unit_price: Optional[float] = None  # Precio por unidad (kg, litro, etc.)
    unit_type: Optional[str] = None
    last_updated: datetime = None
    is_promotion: bool = False
    promotion_end_date: Optional[datetime] = None


@dataclass
class PriceAnalysis:
    """Resultado del análisis de precios"""
    product_name: str
    min_price: float
    max_price: float
    avg_price: float
    median_price: float
    price_variance: float
    best_deals: List[ProductPrice]
    price_trend: str  # "stable", "increasing", "decreasing"
    savings_opportunity: float


class PriceAnalyzer:
    """
    Analizador de precios para optimización de compras.
    
    Funcionalidades:
    - Análisis estadístico de precios
    - Detección de ofertas y promociones
    - Comparación entre tiendas
    - Análisis de tendencias de precios
    - Cálculo de ahorros potenciales
    """
    
    def __init__(self, database_session=None):
        self.db = database_session
        
        # Umbrales para detección de ofertas
        self.discount_threshold = 0.15  # 15% descuento mínimo
        self.outlier_threshold = 2.0    # Desviaciones estándar para outliers
        
    async def get_products_with_prices(
        self,
        product_names: List[str],
        location: Optional[Dict] = None,
        radius_km: float = 10.0
    ) -> Dict[str, List[ProductPrice]]:
        """
        Obtiene productos con sus precios en tiendas cercanas.
        
        Args:
            product_names: Lista de nombres de productos
            location: Ubicación del usuario (lat, lng)
            radius_km: Radio de búsqueda en kilómetros
            
        Returns:
            Dict con productos y sus precios por tienda
        """
        try:
            products_data = {}
            
            for product_name in product_names:
                # Buscar precios del producto
                prices = await self._fetch_product_prices(
                    product_name, location, radius_km
                )
                
                if prices:
                    products_data[product_name] = prices
                else:
                    # Si no se encuentra, buscar productos similares
                    similar_products = await self._find_similar_products(product_name)
                    if similar_products:
                        products_data[product_name] = similar_products
            
            return products_data
            
        except Exception as e:
            logger.error(f"Error obteniendo precios: {str(e)}")
            return {}
    
    async def analyze_product_prices(
        self,
        product_name: str,
        prices: List[ProductPrice]
    ) -> PriceAnalysis:
        """
        Analiza los precios de un producto específico.
        
        Args:
            product_name: Nombre del producto
            prices: Lista de precios del producto
            
        Returns:
            PriceAnalysis: Análisis completo de precios
        """
        if not prices:
            return PriceAnalysis(
                product_name=product_name,
                min_price=0, max_price=0, avg_price=0,
                median_price=0, price_variance=0,
                best_deals=[], price_trend="unknown",
                savings_opportunity=0
            )
        
        # Extraer solo los precios para cálculos estadísticos
        price_values = [p.price for p in prices]
        
        # Cálculos estadísticos básicos
        min_price = min(price_values)
        max_price = max(price_values)
        avg_price = statistics.mean(price_values)
        median_price = statistics.median(price_values)
        price_variance = statistics.variance(price_values) if len(price_values) > 1 else 0
        
        # Identificar mejores ofertas
        best_deals = self._identify_best_deals(prices, avg_price)
        
        # Analizar tendencia de precios
        price_trend = await self._analyze_price_trend(product_name)
        
        # Calcular oportunidad de ahorro
        savings_opportunity = max_price - min_price
        
        return PriceAnalysis(
            product_name=product_name,
            min_price=min_price,
            max_price=max_price,
            avg_price=avg_price,
            median_price=median_price,
            price_variance=price_variance,
            best_deals=best_deals,
            price_trend=price_trend,
            savings_opportunity=savings_opportunity
        )
    
    def _identify_best_deals(
        self,
        prices: List[ProductPrice],
        avg_price: float
    ) -> List[ProductPrice]:
        """
        Identifica las mejores ofertas basándose en precio y descuentos.
        """
        best_deals = []
        
        for price in prices:
            # Criterios para considerar una buena oferta:
            # 1. Precio significativamente menor al promedio
            # 2. Descuento explícito mayor al umbral
            # 3. Promoción activa
            
            is_good_deal = False
            
            # Precio bajo comparado con el promedio
            if price.price < avg_price * (1 - self.discount_threshold):
                is_good_deal = True
            
            # Descuento explícito
            if (price.discount_percentage and 
                price.discount_percentage >= self.discount_threshold * 100):
                is_good_deal = True
            
            # Promoción activa
            if price.is_promotion:
                is_good_deal = True
            
            if is_good_deal:
                best_deals.append(price)
        
        # Ordenar por precio (mejores primero)
        best_deals.sort(key=lambda x: x.price)
        
        return best_deals[:5]  # Top 5 ofertas
    
    async def _analyze_price_trend(self, product_name: str) -> str:
        """
        Analiza la tendencia de precios histórica de un producto.
        """
        try:
            # Obtener precios históricos (últimos 30 días)
            historical_prices = await self._get_historical_prices(product_name, days=30)
            
            if len(historical_prices) < 3:
                return "insufficient_data"
            
            # Calcular tendencia usando regresión lineal simple
            trend_slope = self._calculate_price_trend_slope(historical_prices)
            
            if trend_slope > 0.05:  # Incremento > 5%
                return "increasing"
            elif trend_slope < -0.05:  # Decremento > 5%
                return "decreasing"
            else:
                return "stable"
                
        except Exception as e:
            logger.warning(f"Error analizando tendencia: {str(e)}")
            return "unknown"
    
    def _calculate_price_trend_slope(
        self,
        historical_prices: List[Tuple[datetime, float]]
    ) -> float:
        """
        Calcula la pendiente de la tendencia de precios.
        """
        if len(historical_prices) < 2:
            return 0.0
        
        # Convertir fechas a números (días desde el primer registro)
        first_date = historical_prices[0][0]
        x_values = [(date - first_date).days for date, price in historical_prices]
        y_values = [price for date, price in historical_prices]
        
        # Regresión lineal simple
        n = len(x_values)
        sum_x = sum(x_values)
        sum_y = sum(y_values)
        sum_xy = sum(x * y for x, y in zip(x_values, y_values))
        sum_x2 = sum(x * x for x in x_values)
        
        # Calcular pendiente
        if n * sum_x2 - sum_x * sum_x == 0:
            return 0.0
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        
        # Normalizar por precio promedio para obtener porcentaje
        avg_price = sum_y / n
        return slope / avg_price if avg_price > 0 else 0.0
    
    async def compare_stores_for_product(
        self,
        product_name: str,
        prices: List[ProductPrice]
    ) -> Dict[str, Any]:
        """
        Compara tiendas para un producto específico.
        """
        if not prices:
            return {}
        
        store_comparison = {}
        
        # Agrupar por tienda
        stores_data = {}
        for price in prices:
            if price.store_name not in stores_data:
                stores_data[price.store_name] = []
            stores_data[price.store_name].append(price)
        
        # Analizar cada tienda
        for store_name, store_prices in stores_data.items():
            avg_price = statistics.mean([p.price for p in store_prices])
            min_price = min([p.price for p in store_prices])
            has_promotions = any(p.is_promotion for p in store_prices)
            
            store_comparison[store_name] = {
                "average_price": avg_price,
                "lowest_price": min_price,
                "has_promotions": has_promotions,
                "price_count": len(store_prices)
            }
        
        # Ranking de tiendas por precio
        ranked_stores = sorted(
            store_comparison.items(),
            key=lambda x: x[1]["lowest_price"]
        )
        
        return {
            "store_details": store_comparison,
            "best_store": ranked_stores[0][0] if ranked_stores else None,
            "price_range": {
                "min": min([p.price for p in prices]),
                "max": max([p.price for p in prices])
            }
        }
    
    async def calculate_shopping_list_savings(
        self,
        products_data: Dict[str, List[ProductPrice]]
    ) -> Dict[str, Any]:
        """
        Calcula ahorros potenciales para una lista completa de compras.
        """
        total_savings = 0.0
        product_savings = {}
        best_store_combinations = {}
        
        for product_name, prices in products_data.items():
            if not prices:
                continue
            
            analysis = await self.analyze_product_prices(product_name, prices)
            product_savings[product_name] = {
                "max_savings": analysis.savings_opportunity,
                "best_price": analysis.min_price,
                "worst_price": analysis.max_price,
                "recommended_stores": [deal.store_name for deal in analysis.best_deals[:3]]
            }
            
            total_savings += analysis.savings_opportunity
        
        return {
            "total_potential_savings": total_savings,
            "product_breakdown": product_savings,
            "optimization_opportunities": self._identify_optimization_opportunities(products_data)
        }
    
    def _identify_optimization_opportunities(
        self,
        products_data: Dict[str, List[ProductPrice]]
    ) -> List[Dict]:
        """
        Identifica oportunidades específicas de optimización.
        """
        opportunities = []
        
        # Oportunidad 1: Productos con gran variación de precios
        for product_name, prices in products_data.items():
            if len(prices) < 2:
                continue
            
            price_values = [p.price for p in prices]
            price_range = max(price_values) - min(price_values)
            avg_price = statistics.mean(price_values)
            
            if price_range > avg_price * 0.3:  # Variación > 30%
                opportunities.append({
                    "type": "high_price_variation",
                    "product": product_name,
                    "potential_savings": price_range,
                    "recommendation": f"Comparar precios cuidadosamente para {product_name}"
                })
        
        # Oportunidad 2: Promociones activas
        for product_name, prices in products_data.items():
            active_promotions = [p for p in prices if p.is_promotion]
            if active_promotions:
                opportunities.append({
                    "type": "active_promotion",
                    "product": product_name,
                    "stores_with_promotions": [p.store_name for p in active_promotions],
                    "recommendation": f"Aprovechar promociones en {product_name}"
                })
        
        return opportunities
    
    async def detect_price_anomalies(
        self,
        prices: List[ProductPrice]
    ) -> List[ProductPrice]:
        """
        Detecta precios anómalos (muy altos o muy bajos).
        """
        if len(prices) < 3:
            return []
        
        price_values = [p.price for p in prices]
        mean_price = statistics.mean(price_values)
        std_dev = statistics.stdev(price_values)
        
        anomalies = []
        
        for price in prices:
            # Calcular z-score
            z_score = abs(price.price - mean_price) / std_dev if std_dev > 0 else 0
            
            if z_score > self.outlier_threshold:
                anomalies.append(price)
        
        return anomalies
    
    # Métodos de base de datos (implementación específica)
    async def _fetch_product_prices(
        self,
        product_name: str,
        location: Optional[Dict],
        radius_km: float
    ) -> List[ProductPrice]:
        """Obtiene precios de un producto desde la base de datos"""
        # Implementación específica según la base de datos
        # Por ahora retorna datos simulados
        return []
    
    async def _find_similar_products(self, product_name: str) -> List[ProductPrice]:
        """Busca productos similares si no se encuentra el exacto"""
        # Implementación de búsqueda fuzzy
        return []
    
    async def _get_historical_prices(
        self,
        product_name: str,
        days: int
    ) -> List[Tuple[datetime, float]]:
        """Obtiene precios históricos de un producto"""
        # Implementación específica según la base de datos
        return []


# Funciones de utilidad adicionales

def calculate_unit_price(price: float, quantity: float, unit: str) -> float:
    """
    Calcula el precio por unidad estándar.
    
    Args:
        price: Precio total
        quantity: Cantidad
        unit: Unidad (kg, g, l, ml, etc.)
        
    Returns:
        float: Precio por unidad estándar
    """
    # Convertir a unidades estándar
    if unit.lower() in ['g', 'gr', 'gramos']:
        standard_quantity = quantity / 1000  # Convertir a kg
    elif unit.lower() in ['ml', 'mililitros']:
        standard_quantity = quantity / 1000  # Convertir a litros
    else:
        standard_quantity = quantity
    
    return price / standard_quantity if standard_quantity > 0 else 0


def format_price_comparison(analysis: PriceAnalysis) -> str:
    """
    Formatea un análisis de precios en texto legible.
    """
    return f"""
Análisis de precios para {analysis.product_name}:
- Precio mínimo: ${analysis.min_price:,.0f}
- Precio máximo: ${analysis.max_price:,.0f}
- Precio promedio: ${analysis.avg_price:,.0f}
- Ahorro potencial: ${analysis.savings_opportunity:,.0f}
- Tendencia: {analysis.price_trend}
- Mejores ofertas: {len(analysis.best_deals)} encontradas
"""

