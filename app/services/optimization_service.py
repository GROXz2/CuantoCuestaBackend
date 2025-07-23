"""
Servicio de Optimización de Compras
===================================

Este servicio contiene la lógica principal para optimizar listas de compras
considerando múltiples factores: precio, distancia, tiempo y comodidad.

Autor: Manus AI
Fecha: 2024
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import asyncio
import logging

from ..models.optimization_result import OptimizationResult, ShoppingScenario
from ..models.user_profile import UserProfile
from ..schemas.optimization import OptimizationRequest, OptimizationResponse
from .scoring_service import ScoringService
from .user_profile_service import UserProfileService
from .cache_service import CacheService
from ..utils.distance_calculator import DistanceCalculator
from ..utils.route_optimizer import RouteOptimizer
from ..utils.price_analyzer import PriceAnalyzer

logger = logging.getLogger(__name__)


class OptimizationPriority(Enum):
    """Prioridades de optimización disponibles"""
    AHORRO_MAXIMO = "ahorro_maximo"
    CONVENIENCIA = "conveniencia"
    EQUILIBRIO = "equilibrio"
    TIEMPO_MINIMO = "tiempo_minimo"


@dataclass
class OptimizationWeights:
    """Pesos para la función de optimización"""
    ahorro: float = 0.6
    tiempo: float = 0.2
    distancia: float = 0.1
    comodidad: float = 0.1
    
    def __post_init__(self):
        """Validar que los pesos sumen 1.0"""
        total = self.ahorro + self.tiempo + self.distancia + self.comodidad
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Los pesos deben sumar 1.0, actual: {total}")


class OptimizationService:
    """
    Servicio principal de optimización de compras.
    
    Funcionalidades:
    - Genera múltiples escenarios de compra
    - Calcula scores ponderados para cada escenario
    - Optimiza rutas y combinaciones de supermercados
    - Considera preferencias del usuario
    """
    
    def __init__(
        self,
        scoring_service: ScoringService,
        user_profile_service: UserProfileService,
        cache_service: CacheService,
        distance_calculator: DistanceCalculator,
        route_optimizer: RouteOptimizer,
        price_analyzer: PriceAnalyzer
    ):
        self.scoring_service = scoring_service
        self.user_profile_service = user_profile_service
        self.cache_service = cache_service
        self.distance_calculator = distance_calculator
        self.route_optimizer = route_optimizer
        self.price_analyzer = price_analyzer
        
    async def optimize_shopping_list(
        self,
        request: OptimizationRequest
    ) -> OptimizationResponse:
        """
        Optimiza una lista de compras según las preferencias del usuario.
        
        Args:
            request: Solicitud de optimización con productos y restricciones
            
        Returns:
            OptimizationResponse: Respuesta con escenarios optimizados
        """
        try:
            logger.info(f"Iniciando optimización para {len(request.productos)} productos")
            
            # 1. Cargar perfil del usuario
            user_profile = await self._get_user_profile(request.session_id)
            
            # 2. Verificar cache
            cache_key = self._generate_cache_key(request, user_profile)
            cached_result = await self.cache_service.get_optimization_result(cache_key)
            if cached_result:
                logger.info("Resultado encontrado en cache")
                return cached_result
            
            # 3. Obtener pesos de optimización
            weights = self._get_optimization_weights(request, user_profile)
            
            # 4. Generar escenarios de compra
            scenarios = await self._generate_shopping_scenarios(request, user_profile)
            
            # 5. Calcular scores para cada escenario
            scored_scenarios = await self._score_scenarios(scenarios, weights, request)
            
            # 6. Seleccionar mejores escenarios
            best_scenarios = self._select_best_scenarios(scored_scenarios)
            
            # 7. Generar respuesta
            response = self._build_response(best_scenarios, request, user_profile)
            
            # 8. Guardar en cache
            await self.cache_service.save_optimization_result(cache_key, response)
            
            # 9. Actualizar perfil del usuario
            await self._update_user_profile(request.session_id, request, response)
            
            logger.info(f"Optimización completada. {len(best_scenarios)} escenarios generados")
            return response
            
        except Exception as e:
            logger.error(f"Error en optimización: {str(e)}")
            raise
    
    async def _get_user_profile(self, session_id: Optional[str]) -> Optional[UserProfile]:
        """Obtiene el perfil del usuario si existe"""
        if not session_id:
            return None
        return await self.user_profile_service.get_profile(session_id)
    
    def _get_optimization_weights(
        self,
        request: OptimizationRequest,
        user_profile: Optional[UserProfile]
    ) -> OptimizationWeights:
        """
        Determina los pesos de optimización basándose en:
        1. Pesos explícitos en la request
        2. Preferencias del perfil del usuario
        3. Valores por defecto
        """
        if request.ponderaciones:
            return OptimizationWeights(**request.ponderaciones)
        
        if user_profile and user_profile.preferencias_optimizacion:
            prefs = user_profile.preferencias_optimizacion
            if prefs.prioridad == OptimizationPriority.AHORRO_MAXIMO:
                return OptimizationWeights(ahorro=0.8, tiempo=0.1, distancia=0.05, comodidad=0.05)
            elif prefs.prioridad == OptimizationPriority.CONVENIENCIA:
                return OptimizationWeights(ahorro=0.3, tiempo=0.3, distancia=0.2, comodidad=0.2)
            elif prefs.prioridad == OptimizationPriority.TIEMPO_MINIMO:
                return OptimizationWeights(ahorro=0.2, tiempo=0.6, distancia=0.1, comodidad=0.1)
        
        # Valores por defecto
        return OptimizationWeights()
    
    async def _generate_shopping_scenarios(
        self,
        request: OptimizationRequest,
        user_profile: Optional[UserProfile]
    ) -> List[ShoppingScenario]:
        """
        Genera diferentes escenarios de compra:
        1. Un solo supermercado (por cada cadena disponible)
        2. Dos supermercados (combinaciones óptimas)
        3. Tres supermercados (solo si hay muchos productos)
        """
        scenarios = []
        
        # Obtener productos con precios
        productos_con_precios = await self.price_analyzer.get_products_with_prices(
            request.productos,
            request.ubicacion
        )
        
        # Escenario 1: Un solo supermercado
        single_store_scenarios = await self._generate_single_store_scenarios(
            productos_con_precios, request, user_profile
        )
        scenarios.extend(single_store_scenarios)
        
        # Escenario 2: Dos supermercados
        if len(request.productos) >= 3:  # Solo si vale la pena dividir
            dual_store_scenarios = await self._generate_dual_store_scenarios(
                productos_con_precios, request, user_profile
            )
            scenarios.extend(dual_store_scenarios)
        
        # Escenario 3: Tres supermercados (solo para listas grandes)
        if len(request.productos) >= 8:
            triple_store_scenarios = await self._generate_triple_store_scenarios(
                productos_con_precios, request, user_profile
            )
            scenarios.extend(triple_store_scenarios)
        
        return scenarios
    
    async def _generate_single_store_scenarios(
        self,
        productos_con_precios: Dict,
        request: OptimizationRequest,
        user_profile: Optional[UserProfile]
    ) -> List[ShoppingScenario]:
        """Genera escenarios comprando todo en un solo supermercado"""
        scenarios = []
        
        # Obtener supermercados disponibles
        supermercados = await self._get_available_supermarkets(request.ubicacion)
        
        for supermercado in supermercados:
            scenario = await self._build_single_store_scenario(
                supermercado, productos_con_precios, request
            )
            if scenario:
                scenarios.append(scenario)
        
        return scenarios
    
    async def _generate_dual_store_scenarios(
        self,
        productos_con_precios: Dict,
        request: OptimizationRequest,
        user_profile: Optional[UserProfile]
    ) -> List[ShoppingScenario]:
        """Genera escenarios dividiendo compras entre dos supermercados"""
        scenarios = []
        
        # Lógica para dividir productos entre dos tiendas
        # basándose en precios y ubicación
        
        return scenarios
    
    async def _score_scenarios(
        self,
        scenarios: List[ShoppingScenario],
        weights: OptimizationWeights,
        request: OptimizationRequest
    ) -> List[Tuple[ShoppingScenario, float]]:
        """Calcula el score de cada escenario usando el ScoringService"""
        scored_scenarios = []
        
        for scenario in scenarios:
            score = await self.scoring_service.calculate_scenario_score(
                scenario, weights, request.ubicacion
            )
            scored_scenarios.append((scenario, score))
        
        return scored_scenarios
    
    def _select_best_scenarios(
        self,
        scored_scenarios: List[Tuple[ShoppingScenario, float]]
    ) -> List[ShoppingScenario]:
        """Selecciona los mejores escenarios (top 3-5)"""
        # Ordenar por score descendente
        sorted_scenarios = sorted(scored_scenarios, key=lambda x: x[1], reverse=True)
        
        # Tomar los mejores 3-5 escenarios
        best_scenarios = [scenario for scenario, score in sorted_scenarios[:5]]
        
        return best_scenarios
    
    def _build_response(
        self,
        scenarios: List[ShoppingScenario],
        request: OptimizationRequest,
        user_profile: Optional[UserProfile]
    ) -> OptimizationResponse:
        """Construye la respuesta final con los escenarios optimizados"""
        return OptimizationResponse(
            escenarios=scenarios,
            total_productos=len(request.productos),
            tiempo_procesamiento_ms=0,  # Se calculará en el endpoint
            recomendacion_principal=scenarios[0] if scenarios else None,
            ahorro_potencial=self._calculate_potential_savings(scenarios),
            session_id=request.session_id
        )
    
    def _calculate_potential_savings(self, scenarios: List[ShoppingScenario]) -> float:
        """Calcula el ahorro potencial comparando el mejor vs peor escenario"""
        if len(scenarios) < 2:
            return 0.0
        
        precios = [scenario.precio_total for scenario in scenarios]
        return max(precios) - min(precios)
    
    async def _update_user_profile(
        self,
        session_id: Optional[str],
        request: OptimizationRequest,
        response: OptimizationResponse
    ):
        """Actualiza el perfil del usuario con la nueva información"""
        if not session_id:
            return
        
        await self.user_profile_service.update_shopping_history(
            session_id, request.productos, response.recomendacion_principal
        )
    
    def _generate_cache_key(
        self,
        request: OptimizationRequest,
        user_profile: Optional[UserProfile]
    ) -> str:
        """Genera una clave única para el cache"""
        productos_hash = hash(tuple(sorted(request.productos)))
        ubicacion_hash = hash((request.ubicacion.lat, request.ubicacion.lng)) if request.ubicacion else 0
        profile_hash = hash(str(user_profile.preferencias_optimizacion)) if user_profile else 0
        
        return f"opt_{productos_hash}_{ubicacion_hash}_{profile_hash}"
    
    # Métodos auxiliares adicionales...
    async def _get_available_supermarkets(self, ubicacion):
        """Obtiene supermercados disponibles cerca de la ubicación"""
        pass
    
    async def _build_single_store_scenario(self, supermercado, productos_con_precios, request):
        """Construye un escenario para un solo supermercado"""
        pass

