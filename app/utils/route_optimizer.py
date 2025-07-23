"""
Utilidad de Optimización de Rutas
=================================

Esta utilidad optimiza rutas de compra para minimizar distancia y tiempo,
resolviendo el problema del vendedor viajero (TSP) de forma aproximada.

Autor: Manus AI
Fecha: 2024
"""

from typing import List, Tuple, Dict, Optional
import itertools
import math
import logging
from dataclasses import dataclass

from .distance_calculator import DistanceCalculator, Coordenadas, DistanceResult

logger = logging.getLogger(__name__)


@dataclass
class RouteStop:
    """Representa una parada en la ruta"""
    id: str
    name: str
    coordinates: Coordenadas
    estimated_time_minutes: int = 30  # Tiempo estimado de compra
    priority: int = 1  # 1=alta, 2=media, 3=baja


@dataclass
class OptimizedRoute:
    """Resultado de optimización de ruta"""
    stops: List[RouteStop]
    total_distance_km: float
    total_time_minutes: int
    optimization_method: str
    savings_vs_original: Optional[float] = None


class RouteOptimizer:
    """
    Optimizador de rutas de compra.
    
    Funcionalidades:
    - Optimización de rutas para múltiples tiendas
    - Algoritmos aproximados para TSP
    - Consideración de prioridades y restricciones
    - Optimización por tiempo vs distancia
    """
    
    def __init__(self, distance_calculator: DistanceCalculator):
        self.distance_calculator = distance_calculator
        
        # Límites para diferentes algoritmos
        self.brute_force_limit = 6  # Máximo para fuerza bruta
        self.nearest_neighbor_limit = 20  # Máximo para vecino más cercano
    
    async def optimize_shopping_route(
        self,
        origin: Coordenadas,
        stores: List[RouteStop],
        return_to_origin: bool = False,
        optimize_for: str = "time"  # "time", "distance", "balanced"
    ) -> OptimizedRoute:
        """
        Optimiza la ruta de compras para visitar múltiples tiendas.
        
        Args:
            origin: Punto de inicio
            stores: Lista de tiendas a visitar
            return_to_origin: Si debe regresar al punto de inicio
            optimize_for: Criterio de optimización
            
        Returns:
            OptimizedRoute: Ruta optimizada
        """
        try:
            if not stores:
                return OptimizedRoute(
                    stops=[],
                    total_distance_km=0.0,
                    total_time_minutes=0,
                    optimization_method="empty"
                )
            
            # Seleccionar algoritmo según número de tiendas
            if len(stores) <= self.brute_force_limit:
                result = await self._brute_force_optimization(
                    origin, stores, return_to_origin, optimize_for
                )
            elif len(stores) <= self.nearest_neighbor_limit:
                result = await self._nearest_neighbor_optimization(
                    origin, stores, return_to_origin, optimize_for
                )
            else:
                result = await self._greedy_optimization(
                    origin, stores, return_to_origin, optimize_for
                )
            
            # Calcular ahorros vs ruta original
            original_route = await self._calculate_original_route_cost(
                origin, stores, return_to_origin, optimize_for
            )
            
            if optimize_for == "time":
                savings = original_route - result.total_time_minutes
            else:
                savings = original_route - result.total_distance_km
            
            result.savings_vs_original = max(0, savings)
            
            logger.info(f"Ruta optimizada: {len(stores)} tiendas, "
                       f"método: {result.optimization_method}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error optimizando ruta: {str(e)}")
            # Retornar ruta simple en caso de error
            return await self._simple_route(origin, stores, return_to_origin)
    
    async def _brute_force_optimization(
        self,
        origin: Coordenadas,
        stores: List[RouteStop],
        return_to_origin: bool,
        optimize_for: str
    ) -> OptimizedRoute:
        """
        Optimización por fuerza bruta (para pocas tiendas).
        Prueba todas las permutaciones posibles.
        """
        best_route = None
        best_cost = float('inf')
        
        # Probar todas las permutaciones
        for permutation in itertools.permutations(stores):
            route_cost = await self._calculate_route_cost(
                origin, list(permutation), return_to_origin, optimize_for
            )
            
            if route_cost < best_cost:
                best_cost = route_cost
                best_route = list(permutation)
        
        # Calcular métricas finales
        total_distance, total_time = await self._calculate_route_metrics(
            origin, best_route, return_to_origin
        )
        
        return OptimizedRoute(
            stops=best_route,
            total_distance_km=total_distance,
            total_time_minutes=total_time,
            optimization_method="brute_force"
        )
    
    async def _nearest_neighbor_optimization(
        self,
        origin: Coordenadas,
        stores: List[RouteStop],
        return_to_origin: bool,
        optimize_for: str
    ) -> OptimizedRoute:
        """
        Algoritmo del vecino más cercano.
        Siempre va a la tienda más cercana no visitada.
        """
        route = []
        remaining_stores = stores.copy()
        current_position = origin
        
        while remaining_stores:
            # Encontrar la tienda más cercana
            nearest_store = None
            min_cost = float('inf')
            
            for store in remaining_stores:
                cost = await self._calculate_segment_cost(
                    current_position, store.coordinates, optimize_for
                )
                
                # Aplicar factor de prioridad
                adjusted_cost = cost * store.priority
                
                if adjusted_cost < min_cost:
                    min_cost = adjusted_cost
                    nearest_store = store
            
            # Agregar a la ruta y actualizar posición
            route.append(nearest_store)
            remaining_stores.remove(nearest_store)
            current_position = nearest_store.coordinates
        
        # Calcular métricas finales
        total_distance, total_time = await self._calculate_route_metrics(
            origin, route, return_to_origin
        )
        
        return OptimizedRoute(
            stops=route,
            total_distance_km=total_distance,
            total_time_minutes=total_time,
            optimization_method="nearest_neighbor"
        )
    
    async def _greedy_optimization(
        self,
        origin: Coordenadas,
        stores: List[RouteStop],
        return_to_origin: bool,
        optimize_for: str
    ) -> OptimizedRoute:
        """
        Algoritmo greedy mejorado para muchas tiendas.
        Combina vecino más cercano con optimizaciones locales.
        """
        # Empezar con vecino más cercano
        initial_route = await self._nearest_neighbor_optimization(
            origin, stores, return_to_origin, optimize_for
        )
        
        # Aplicar optimización 2-opt para mejorar
        optimized_route = await self._two_opt_improvement(
            origin, initial_route.stops, return_to_origin, optimize_for
        )
        
        # Calcular métricas finales
        total_distance, total_time = await self._calculate_route_metrics(
            origin, optimized_route, return_to_origin
        )
        
        return OptimizedRoute(
            stops=optimized_route,
            total_distance_km=total_distance,
            total_time_minutes=total_time,
            optimization_method="greedy_2opt"
        )
    
    async def _two_opt_improvement(
        self,
        origin: Coordenadas,
        route: List[RouteStop],
        return_to_origin: bool,
        optimize_for: str
    ) -> List[RouteStop]:
        """
        Mejora una ruta usando el algoritmo 2-opt.
        Intercambia segmentos de la ruta para reducir cruces.
        """
        if len(route) < 4:
            return route
        
        improved = True
        current_route = route.copy()
        
        while improved:
            improved = False
            
            for i in range(len(current_route) - 1):
                for j in range(i + 2, len(current_route)):
                    # Crear nueva ruta intercambiando segmento
                    new_route = (current_route[:i + 1] + 
                                current_route[i + 1:j + 1][::-1] + 
                                current_route[j + 1:])
                    
                    # Calcular costo de ambas rutas
                    current_cost = await self._calculate_route_cost(
                        origin, current_route, return_to_origin, optimize_for
                    )
                    new_cost = await self._calculate_route_cost(
                        origin, new_route, return_to_origin, optimize_for
                    )
                    
                    # Si la nueva ruta es mejor, adoptarla
                    if new_cost < current_cost:
                        current_route = new_route
                        improved = True
                        break
                
                if improved:
                    break
        
        return current_route
    
    async def _calculate_route_cost(
        self,
        origin: Coordenadas,
        stores: List[RouteStop],
        return_to_origin: bool,
        optimize_for: str
    ) -> float:
        """
        Calcula el costo total de una ruta según el criterio de optimización.
        """
        if not stores:
            return 0.0
        
        total_cost = 0.0
        current_position = origin
        
        # Costo de ir a cada tienda
        for store in stores:
            segment_cost = await self._calculate_segment_cost(
                current_position, store.coordinates, optimize_for
            )
            total_cost += segment_cost
            
            # Agregar tiempo de compra si optimizamos por tiempo
            if optimize_for in ["time", "balanced"]:
                total_cost += store.estimated_time_minutes
            
            current_position = store.coordinates
        
        # Costo de regresar al origen
        if return_to_origin:
            return_cost = await self._calculate_segment_cost(
                current_position, origin, optimize_for
            )
            total_cost += return_cost
        
        return total_cost
    
    async def _calculate_segment_cost(
        self,
        origin: Coordenadas,
        destination: Coordenadas,
        optimize_for: str
    ) -> float:
        """
        Calcula el costo de un segmento según el criterio de optimización.
        """
        distance_result = await self.distance_calculator.calculate_distance(
            origin, destination
        )
        
        if optimize_for == "distance":
            return distance_result.distance_km
        elif optimize_for == "time":
            return distance_result.duration_minutes or (distance_result.distance_km * 2)
        elif optimize_for == "balanced":
            # Combinar distancia y tiempo con pesos
            distance_weight = 0.4
            time_weight = 0.6
            time_minutes = distance_result.duration_minutes or (distance_result.distance_km * 2)
            return (distance_result.distance_km * distance_weight + 
                   time_minutes * time_weight)
        else:
            return distance_result.distance_km
    
    async def _calculate_route_metrics(
        self,
        origin: Coordenadas,
        stores: List[RouteStop],
        return_to_origin: bool
    ) -> Tuple[float, int]:
        """
        Calcula distancia total y tiempo total de una ruta.
        
        Returns:
            Tuple[float, int]: (distancia_km, tiempo_minutos)
        """
        if not stores:
            return 0.0, 0
        
        total_distance = 0.0
        total_time = 0
        current_position = origin
        
        # Calcular para cada segmento
        for store in stores:
            distance_result = await self.distance_calculator.calculate_distance(
                current_position, store.coordinates
            )
            
            total_distance += distance_result.distance_km
            total_time += (distance_result.duration_minutes or 
                          int(distance_result.distance_km * 2))
            total_time += store.estimated_time_minutes  # Tiempo de compra
            
            current_position = store.coordinates
        
        # Regresar al origen si es necesario
        if return_to_origin:
            distance_result = await self.distance_calculator.calculate_distance(
                current_position, origin
            )
            total_distance += distance_result.distance_km
            total_time += (distance_result.duration_minutes or 
                          int(distance_result.distance_km * 2))
        
        return round(total_distance, 2), total_time
    
    async def _calculate_original_route_cost(
        self,
        origin: Coordenadas,
        stores: List[RouteStop],
        return_to_origin: bool,
        optimize_for: str
    ) -> float:
        """
        Calcula el costo de la ruta original (sin optimizar).
        """
        return await self._calculate_route_cost(
            origin, stores, return_to_origin, optimize_for
        )
    
    async def _simple_route(
        self,
        origin: Coordenadas,
        stores: List[RouteStop],
        return_to_origin: bool
    ) -> OptimizedRoute:
        """
        Crea una ruta simple sin optimización (fallback).
        """
        total_distance, total_time = await self._calculate_route_metrics(
            origin, stores, return_to_origin
        )
        
        return OptimizedRoute(
            stops=stores,
            total_distance_km=total_distance,
            total_time_minutes=total_time,
            optimization_method="simple"
        )
    
    def create_route_summary(self, route: OptimizedRoute) -> Dict:
        """
        Crea un resumen legible de la ruta optimizada.
        """
        summary = {
            "total_stops": len(route.stops),
            "total_distance_km": route.total_distance_km,
            "total_time_minutes": route.total_time_minutes,
            "total_time_formatted": self._format_time(route.total_time_minutes),
            "optimization_method": route.optimization_method,
            "savings_vs_original": route.savings_vs_original,
            "route_details": []
        }
        
        for i, stop in enumerate(route.stops):
            summary["route_details"].append({
                "order": i + 1,
                "store_name": stop.name,
                "estimated_shopping_time": stop.estimated_time_minutes,
                "priority": stop.priority
            })
        
        return summary
    
    def _format_time(self, minutes: int) -> str:
        """Formatea tiempo en formato legible"""
        hours = minutes // 60
        mins = minutes % 60
        
        if hours > 0:
            return f"{hours}h {mins}m"
        else:
            return f"{mins}m"


# Funciones de utilidad adicionales

def calculate_route_efficiency(route: OptimizedRoute, direct_distance: float) -> float:
    """
    Calcula la eficiencia de una ruta comparada con la distancia directa.
    
    Returns:
        float: Eficiencia (0-1, donde 1 es perfecta)
    """
    if direct_distance == 0:
        return 1.0
    
    efficiency = direct_distance / route.total_distance_km
    return min(1.0, efficiency)


def estimate_fuel_cost(distance_km: float, fuel_price_per_liter: float = 1500) -> float:
    """
    Estima el costo de combustible para una ruta.
    
    Args:
        distance_km: Distancia total en kilómetros
        fuel_price_per_liter: Precio del combustible por litro
        
    Returns:
        float: Costo estimado en pesos chilenos
    """
    # Asumiendo consumo promedio de 10 km/litro
    liters_needed = distance_km / 10
    return liters_needed * fuel_price_per_liter

