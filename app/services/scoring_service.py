"""
Servicio de Scoring y Ponderación
=================================

Este servicio calcula scores ponderados para diferentes escenarios de compra,
considerando múltiples factores como precio, tiempo, distancia y comodidad.

Autor: Manus AI
Fecha: 2024
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import math
import logging

from ..models.optimization_result import ShoppingScenario
from ..schemas.optimization import Ubicacion
from ..utils.distance_calculator import DistanceCalculator

logger = logging.getLogger(__name__)


@dataclass
class ScoreComponents:
    """Componentes individuales del score"""
    ahorro_score: float
    tiempo_score: float
    distancia_score: float
    comodidad_score: float
    score_total: float
    
    def to_dict(self) -> Dict:
        return {
            "ahorro": self.ahorro_score,
            "tiempo": self.tiempo_score,
            "distancia": self.distancia_score,
            "comodidad": self.comodidad_score,
            "total": self.score_total
        }


class ScoringService:
    """
    Servicio para calcular scores ponderados de escenarios de compra.
    
    Funcionalidades:
    - Normalización de métricas (precio, tiempo, distancia)
    - Cálculo de scores individuales por componente
    - Aplicación de pesos de optimización
    - Generación de scores finales comparables
    """
    
    def __init__(self, distance_calculator: DistanceCalculator):
        self.distance_calculator = distance_calculator
        
        # Valores de referencia para normalización
        self.reference_values = {
            "precio_max": 100000,  # $100,000 CLP como referencia máxima
            "tiempo_max": 180,     # 3 horas como tiempo máximo
            "distancia_max": 50,   # 50 km como distancia máxima
            "comodidad_max": 10    # Score de comodidad máximo
        }
    
    async def calculate_scenario_score(
        self,
        scenario: ShoppingScenario,
        weights: 'OptimizationWeights',
        ubicacion_usuario: Optional[Ubicacion] = None
    ) -> float:
        """
        Calcula el score total de un escenario de compra.
        
        Args:
            scenario: Escenario de compra a evaluar
            weights: Pesos de optimización
            ubicacion_usuario: Ubicación del usuario para cálculos de distancia
            
        Returns:
            float: Score total del escenario (0-1, donde 1 es mejor)
        """
        try:
            # Calcular componentes individuales
            components = await self._calculate_score_components(
                scenario, ubicacion_usuario
            )
            
            # Aplicar pesos
            score_total = (
                components.ahorro_score * weights.ahorro +
                components.tiempo_score * weights.tiempo +
                components.distancia_score * weights.distancia +
                components.comodidad_score * weights.comodidad
            )
            
            # Actualizar el score total en los componentes
            components.score_total = score_total
            
            # Guardar componentes en el escenario para debugging
            scenario.score_components = components.to_dict()
            
            logger.debug(f"Score calculado: {score_total:.3f} para escenario {scenario.id}")
            return score_total
            
        except Exception as e:
            logger.error(f"Error calculando score: {str(e)}")
            return 0.0
    
    async def _calculate_score_components(
        self,
        scenario: ShoppingScenario,
        ubicacion_usuario: Optional[Ubicacion]
    ) -> ScoreComponents:
        """Calcula cada componente del score por separado"""
        
        # 1. Score de ahorro (precio)
        ahorro_score = self._calculate_ahorro_score(scenario)
        
        # 2. Score de tiempo
        tiempo_score = self._calculate_tiempo_score(scenario)
        
        # 3. Score de distancia
        distancia_score = await self._calculate_distancia_score(scenario, ubicacion_usuario)
        
        # 4. Score de comodidad
        comodidad_score = self._calculate_comodidad_score(scenario)
        
        return ScoreComponents(
            ahorro_score=ahorro_score,
            tiempo_score=tiempo_score,
            distancia_score=distancia_score,
            comodidad_score=comodidad_score,
            score_total=0.0  # Se calculará después
        )
    
    def _calculate_ahorro_score(self, scenario: ShoppingScenario) -> float:
        """
        Calcula el score de ahorro basado en el precio total.
        
        Lógica:
        - Precio más bajo = score más alto
        - Normalizado entre 0 y 1
        - Usa función inversa para que menor precio = mejor score
        """
        precio_total = scenario.precio_total
        
        # Normalizar precio (0-1)
        precio_normalizado = min(precio_total / self.reference_values["precio_max"], 1.0)
        
        # Invertir para que menor precio = mejor score
        ahorro_score = 1.0 - precio_normalizado
        
        # Aplicar función de mejora para amplificar diferencias
        ahorro_score = self._apply_enhancement_function(ahorro_score)
        
        return max(0.0, min(1.0, ahorro_score))
    
    def _calculate_tiempo_score(self, scenario: ShoppingScenario) -> float:
        """
        Calcula el score de tiempo basado en el tiempo total estimado.
        
        Incluye:
        - Tiempo de viaje entre tiendas
        - Tiempo estimado de compra en cada tienda
        - Tiempo de espera/cola
        """
        tiempo_total = scenario.tiempo_total_minutos
        
        # Normalizar tiempo (0-1)
        tiempo_normalizado = min(tiempo_total / self.reference_values["tiempo_max"], 1.0)
        
        # Invertir para que menor tiempo = mejor score
        tiempo_score = 1.0 - tiempo_normalizado
        
        # Aplicar función de mejora
        tiempo_score = self._apply_enhancement_function(tiempo_score)
        
        return max(0.0, min(1.0, tiempo_score))
    
    async def _calculate_distancia_score(
        self,
        scenario: ShoppingScenario,
        ubicacion_usuario: Optional[Ubicacion]
    ) -> float:
        """
        Calcula el score de distancia basado en la distancia total a recorrer.
        
        Si no hay ubicación del usuario, usa un score neutro.
        """
        if not ubicacion_usuario:
            return 0.5  # Score neutro si no hay ubicación
        
        try:
            # Calcular distancia total del recorrido
            distancia_total = await self._calculate_total_distance(
                scenario, ubicacion_usuario
            )
            
            # Normalizar distancia (0-1)
            distancia_normalizada = min(
                distancia_total / self.reference_values["distancia_max"], 1.0
            )
            
            # Invertir para que menor distancia = mejor score
            distancia_score = 1.0 - distancia_normalizada
            
            # Aplicar función de mejora
            distancia_score = self._apply_enhancement_function(distancia_score)
            
            return max(0.0, min(1.0, distancia_score))
            
        except Exception as e:
            logger.warning(f"Error calculando distancia: {str(e)}")
            return 0.5  # Score neutro en caso de error
    
    def _calculate_comodidad_score(self, scenario: ShoppingScenario) -> float:
        """
        Calcula el score de comodidad basado en factores como:
        - Número de tiendas a visitar (menos = más cómodo)
        - Facilidades de las tiendas (parking, horarios)
        - Familiaridad del usuario con las tiendas
        """
        comodidad_total = 0.0
        
        # Factor 1: Número de tiendas (menos tiendas = más cómodo)
        num_tiendas = len(scenario.tiendas)
        if num_tiendas == 1:
            comodidad_tiendas = 1.0
        elif num_tiendas == 2:
            comodidad_tiendas = 0.7
        elif num_tiendas == 3:
            comodidad_tiendas = 0.4
        else:
            comodidad_tiendas = 0.2
        
        comodidad_total += comodidad_tiendas * 0.6  # 60% del peso
        
        # Factor 2: Facilidades promedio de las tiendas
        facilidades_promedio = sum(
            tienda.score_comodidad for tienda in scenario.tiendas
        ) / len(scenario.tiendas)
        
        facilidades_normalizado = facilidades_promedio / self.reference_values["comodidad_max"]
        comodidad_total += facilidades_normalizado * 0.4  # 40% del peso
        
        return max(0.0, min(1.0, comodidad_total))
    
    async def _calculate_total_distance(
        self,
        scenario: ShoppingScenario,
        ubicacion_usuario: Ubicacion
    ) -> float:
        """
        Calcula la distancia total del recorrido:
        Usuario -> Tienda1 -> Tienda2 -> ... -> Usuario
        """
        if not scenario.tiendas:
            return 0.0
        
        distancia_total = 0.0
        ubicacion_actual = ubicacion_usuario
        
        # Recorrer todas las tiendas
        for tienda in scenario.tiendas:
            distancia = await self.distance_calculator.calculate_distance(
                ubicacion_actual, tienda.ubicacion
            )
            distancia_total += distancia
            ubicacion_actual = tienda.ubicacion
        
        # Regresar al punto de origen (opcional)
        # distancia_regreso = await self.distance_calculator.calculate_distance(
        #     ubicacion_actual, ubicacion_usuario
        # )
        # distancia_total += distancia_regreso
        
        return distancia_total
    
    def _apply_enhancement_function(self, score: float) -> float:
        """
        Aplica una función de mejora para amplificar diferencias entre scores.
        
        Usa una función sigmoide modificada para hacer más pronunciadas
        las diferencias entre opciones buenas y malas.
        """
        # Función sigmoide centrada en 0.5
        enhanced = 1 / (1 + math.exp(-10 * (score - 0.5)))
        return enhanced
    
    def calculate_comparative_scores(
        self,
        scenarios: List[ShoppingScenario]
    ) -> Dict[str, Dict]:
        """
        Calcula scores comparativos entre escenarios.
        
        Útil para mostrar al usuario por qué un escenario es mejor que otro.
        """
        if not scenarios:
            return {}
        
        comparative_data = {}
        
        # Encontrar valores mínimos y máximos para comparación
        precios = [s.precio_total for s in scenarios]
        tiempos = [s.tiempo_total_minutos for s in scenarios]
        
        precio_min, precio_max = min(precios), max(precios)
        tiempo_min, tiempo_max = min(tiempos), max(tiempos)
        
        for scenario in scenarios:
            comparative_data[scenario.id] = {
                "ahorro_vs_mas_caro": precio_max - scenario.precio_total,
                "tiempo_vs_mas_rapido": scenario.tiempo_total_minutos - tiempo_min,
                "ranking_precio": sorted(precios).index(scenario.precio_total) + 1,
                "ranking_tiempo": sorted(tiempos).index(scenario.tiempo_total_minutos) + 1
            }
        
        return comparative_data
    
    def explain_score(self, scenario: ShoppingScenario) -> Dict:
        """
        Genera una explicación detallada del score de un escenario.
        
        Útil para debugging y para mostrar al usuario por qué
        se recomendó un escenario específico.
        """
        if not hasattr(scenario, 'score_components'):
            return {"error": "Score components not available"}
        
        components = scenario.score_components
        
        explanation = {
            "score_total": components["total"],
            "breakdown": {
                "ahorro": {
                    "score": components["ahorro"],
                    "descripcion": f"Precio total: ${scenario.precio_total:,.0f}"
                },
                "tiempo": {
                    "score": components["tiempo"],
                    "descripcion": f"Tiempo total: {scenario.tiempo_total_minutos} minutos"
                },
                "distancia": {
                    "score": components["distancia"],
                    "descripcion": f"Distancia total: {getattr(scenario, 'distancia_total_km', 'N/A')} km"
                },
                "comodidad": {
                    "score": components["comodidad"],
                    "descripcion": f"Tiendas a visitar: {len(scenario.tiendas)}"
                }
            },
            "fortalezas": self._identify_strengths(components),
            "debilidades": self._identify_weaknesses(components)
        }
        
        return explanation
    
    def _identify_strengths(self, components: Dict) -> List[str]:
        """Identifica las fortalezas de un escenario"""
        strengths = []
        
        if components["ahorro"] > 0.7:
            strengths.append("Excelente precio")
        if components["tiempo"] > 0.7:
            strengths.append("Muy rápido")
        if components["distancia"] > 0.7:
            strengths.append("Muy cerca")
        if components["comodidad"] > 0.7:
            strengths.append("Muy cómodo")
        
        return strengths
    
    def _identify_weaknesses(self, components: Dict) -> List[str]:
        """Identifica las debilidades de un escenario"""
        weaknesses = []
        
        if components["ahorro"] < 0.3:
            weaknesses.append("Precio alto")
        if components["tiempo"] < 0.3:
            weaknesses.append("Toma mucho tiempo")
        if components["distancia"] < 0.3:
            weaknesses.append("Muy lejos")
        if components["comodidad"] < 0.3:
            weaknesses.append("Poco cómodo")
        
        return weaknesses

