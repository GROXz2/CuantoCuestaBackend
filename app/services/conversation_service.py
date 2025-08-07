"""
Conversation Service - Sistema de Gestión de Contexto Conversacional
==================================================================

Este servicio implementa un sistema sofisticado de gestión de contexto para superar
las limitaciones de memoria de ChatGPT, utilizando Weighted Moving Average con 
Contextual Anchors para mantener coherencia conversacional y detectar cambios de contexto.

Arquitectura: Weighted Moving Average con Contextual Anchors
- Anclas contextuales que mantienen estabilidad
- Promedios móviles ponderados para adaptabilidad
- Detección avanzada de drift contextual
- Sistema de anonimización para privacidad

Autor: Sistema de Optimización de Compras
Fecha: 2024
"""

import hashlib
import json
import logging
import math
import numpy as np
from collections import deque
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
import asyncio
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ChangeType(Enum):
    """Tipos de cambios de contexto detectables"""
    LOCATION_DRIFT = "location_drift"
    PREFERENCE_SHIFT = "preference_shift"
    TEMPORAL_CHANGE = "temporal_change"
    SATISFACTION_DECLINE = "satisfaction_decline"
    SEASONAL_CHANGE = "seasonal_change"
    ERRATIC_BEHAVIOR = "erratic_behavior"


class DriftDetectionAlgorithm(Enum):
    """Algoritmos disponibles para detección de drift"""
    CUSUM = "cusum"
    PAGE_HINKLEY = "page_hinkley"
    MAHALANOBIS = "mahalanobis_distance"
    VARIANCE_TEST = "variance_test"


@dataclass
class ContextualAnchor:
    """
    Representa un ancla contextual que mantiene estabilidad en el perfil del usuario
    """
    name: str
    weight: float  # Importancia relativa (0-1)
    stability_threshold: float  # Cuánto cambio tolera antes de considerar drift
    decay_rate: float  # Qué tan rápido se adapta a nuevos valores
    current_value: Any = None
    confidence: float = 0.0
    last_updated: datetime = None
    update_count: int = 0
    update_history: List[Dict] = None

    def __post_init__(self):
        if self.last_updated is None:
            self.last_updated = datetime.now()
        if self.update_history is None:
            self.update_history = []


@dataclass
class UserInteraction:
    """
    Representa una interacción del usuario con el sistema
    """
    interaction_id: str
    user_id: str
    timestamp: datetime
    productos: List[str]
    ubicacion: Tuple[float, float]  # (lat, lng)
    decision_tomada: str  # "ahorro", "equilibrio", "conveniencia"
    supermercados_visitados: List[str]
    satisfaccion: float  # 1.0 - 5.0
    context_data: Dict = None

    def __post_init__(self):
        if self.context_data is None:
            self.context_data = {}


@dataclass
class DriftDetectionResult:
    """
    Resultado de la detección de drift contextual
    """
    has_drift: bool
    drift_type: Optional[ChangeType]
    confidence: float
    affected_anchors: List[str]
    detection_algorithm: DriftDetectionAlgorithm
    magnitude: float
    recommended_action: str


class WeightedMovingAverage:
    """
    Implementa sistema de promedio móvil ponderado con pesos exponenciales
    """
    
    def __init__(self, window_size: int = 20, alpha: float = 0.3):
        self.window_size = window_size
        self.alpha = alpha  # Factor de suavizado exponencial
        self.data_points = deque(maxlen=window_size)
        self.weights = self._calculate_weights()
    
    def _calculate_weights(self) -> np.ndarray:
        """Calcula pesos exponenciales: más reciente = más importante"""
        weights = []
        for i in range(self.window_size):
            weight = self.alpha * (1 - self.alpha) ** i
            weights.append(weight)
        return np.array(weights[::-1])  # Invertir para que el más reciente tenga mayor peso
    
    def update(self, new_value: float, timestamp: datetime) -> float:
        """Actualiza con nuevo valor y retorna promedio ponderado"""
        age_weight = self._calculate_age_weight(timestamp)
        
        self.data_points.append({
            'value': new_value,
            'timestamp': timestamp,
            'age_weight': age_weight
        })
        
        return self._calculate_weighted_average()
    
    def _calculate_age_weight(self, timestamp: datetime) -> float:
        """Calcula peso basado en la antigüedad del dato"""
        now = datetime.now()
        age_hours = (now - timestamp).total_seconds() / 3600
        
        # Peso decae exponencialmente con la edad
        return math.exp(-age_hours / 168)  # Half-life de 1 semana
    
    def _calculate_weighted_average(self) -> float:
        """Calcula promedio ponderado de los datos actuales"""
        if not self.data_points:
            return 0.0
        
        total_weight = 0.0
        weighted_sum = 0.0
        
        for i, point in enumerate(self.data_points):
            if i < len(self.weights):
                weight = self.weights[i] * point['age_weight']
                weighted_sum += point['value'] * weight
                total_weight += weight
        
        return weighted_sum / total_weight if total_weight > 0 else 0.0


class LocationHasher:
    """
    Maneja la anonimización de ubicaciones geográficas
    """
    
    @staticmethod
    def create_location_hash(lat: float, lng: float, precision_level: str = "medium") -> Dict[str, str]:
        """
        Crea hash de ubicación que permite agrupación sin revelar ubicación exacta
        """
        precision_configs = {
            "high": 0.001,    # ~100m de precisión
            "medium": 0.01,   # ~1km de precisión  
            "low": 0.1        # ~10km de precisión
        }
        
        precision = precision_configs.get(precision_level, 0.01)
        
        # Redondear coordenadas según precisión
        rounded_lat = round(lat / precision) * precision
        rounded_lng = round(lng / precision) * precision
        
        # Crear hash determinístico
        location_string = f"{rounded_lat:.6f},{rounded_lng:.6f}"
        location_hash = hashlib.sha256(location_string.encode()).hexdigest()[:16]
        
        return {
            "hash": location_hash,
            "region_code": LocationHasher._generate_region_code(rounded_lat, rounded_lng),
            "precision_level": precision_level
        }
    
    @staticmethod
    def _generate_region_code(lat: float, lng: float) -> str:
        """Genera código de región general para agrupación"""
        # Ejemplo para Chile
        if -33.7 <= lat <= -33.2 and -70.9 <= lng <= -70.4:
            return "RM_CENTRO"  # Santiago Centro
        elif -33.5 <= lat <= -33.2 and -70.7 <= lng <= -70.4:
            return "RM_ORIENTE"  # Las Condes, Providencia
        elif -33.0 <= lat <= -32.5 and -71.8 <= lng <= -71.2:
            return "VAL_CENTRO"  # Valparaíso
        else:
            return "OTHER"


class DriftDetector:
    """
    Implementa múltiples algoritmos para detectar cambios de contexto
    """
    
    def __init__(self):
        self.cusum_positive = 0.0
        self.cusum_negative = 0.0
        self.page_hinkley_cumsum = 0.0
        self.page_hinkley_min = 0.0
        self.page_hinkley_max = 0.0
    
    def cusum_test(self, historical_decisions: List[str], new_decision: str, 
                   sensitivity: float = 0.5) -> Dict[str, Any]:
        """
        Detecta cambios en la media de las decisiones del usuario usando CUSUM
        """
        decision_encoding = {"ahorro": 1, "equilibrio": 2, "conveniencia": 3}
        
        if not historical_decisions:
            return {"change_detected": False, "reason": "no_historical_data"}
        
        # Calcular media histórica
        historical_values = [decision_encoding.get(d, 2) for d in historical_decisions]
        historical_mean = np.mean(historical_values)
        
        # Parámetros CUSUM
        target_shift = sensitivity
        decision_limit = 3.0
        
        # Calcular CUSUM
        new_value = decision_encoding.get(new_decision, 2)
        deviation = new_value - historical_mean
        
        # Actualizar acumuladores CUSUM
        self.cusum_positive = max(0, self.cusum_positive + deviation - target_shift/2)
        self.cusum_negative = max(0, self.cusum_negative - deviation - target_shift/2)
        
        # Detectar cambio
        change_detected = (self.cusum_positive > decision_limit or 
                          self.cusum_negative > decision_limit)
        
        return {
            "change_detected": change_detected,
            "magnitude": max(self.cusum_positive, self.cusum_negative),
            "direction": "increase" if self.cusum_positive > self.cusum_negative else "decrease",
            "confidence": min(1.0, max(self.cusum_positive, self.cusum_negative) / decision_limit)
        }
    
    def page_hinkley_test(self, data_stream: List[float], delta: float = 0.1, 
                         lambda_threshold: float = 5.0) -> Dict[str, Any]:
        """
        Detecta cambios abruptos en secuencias temporales usando Page-Hinkley
        """
        change_points = []
        cumulative_sum = 0
        min_cumulative = 0
        max_cumulative = 0
        
        for i, value in enumerate(data_stream):
            cumulative_sum += value - delta
            min_cumulative = min(min_cumulative, cumulative_sum)
            max_cumulative = max(max_cumulative, cumulative_sum)
            
            # Detectar cambio hacia arriba
            if cumulative_sum - min_cumulative > lambda_threshold:
                change_points.append({
                    "index": i,
                    "type": "upward_shift",
                    "magnitude": cumulative_sum - min_cumulative,
                    "confidence": min(1.0, (cumulative_sum - min_cumulative) / lambda_threshold)
                })
                cumulative_sum = 0
                min_cumulative = 0
                max_cumulative = 0
            
            # Detectar cambio hacia abajo
            elif max_cumulative - cumulative_sum > lambda_threshold:
                change_points.append({
                    "index": i,
                    "type": "downward_shift",
                    "magnitude": max_cumulative - cumulative_sum,
                    "confidence": min(1.0, (max_cumulative - cumulative_sum) / lambda_threshold)
                })
                cumulative_sum = 0
                min_cumulative = 0
                max_cumulative = 0
        
        return {
            "changes_detected": len(change_points) > 0,
            "change_points": change_points,
            "most_recent_change": change_points[-1] if change_points else None
        }
    
    def detect_multivariate_outliers(self, new_interaction: UserInteraction, 
                                   historical_interactions: List[UserInteraction],
                                   home_location: Tuple[float, float]) -> Dict[str, Any]:
        """
        Usa distancia de Mahalanobis para detectar interacciones anómalas
        """
        if len(historical_interactions) < 10:
            return {"is_outlier": False, "reason": "insufficient_data"}
        
        # Extraer features numéricas
        def extract_features(interaction: UserInteraction) -> List[float]:
            distance_from_home = self._calculate_distance(home_location, interaction.ubicacion)
            return [
                distance_from_home,
                interaction.satisfaccion,
                len(interaction.productos),
                interaction.timestamp.hour,
                interaction.timestamp.weekday(),
                self._encode_decision_type(interaction.decision_tomada)
            ]
        
        # Preparar datos históricos
        historical_features = [extract_features(i) for i in historical_interactions[-50:]]
        historical_matrix = np.array(historical_features)
        
        # Calcular estadísticas
        mean_vector = np.mean(historical_matrix, axis=0)
        cov_matrix = np.cov(historical_matrix.T)
        
        # Features de la nueva interacción
        new_features = np.array(extract_features(new_interaction))
        
        try:
            # Calcular distancia de Mahalanobis
            diff = new_features - mean_vector
            mahalanobis_distance = np.sqrt(diff.T @ np.linalg.inv(cov_matrix) @ diff)
            
            # Threshold basado en distribución chi-cuadrado (6 variables, 95% confianza)
            threshold = 12.59
            
            return {
                "is_outlier": mahalanobis_distance > threshold,
                "distance": float(mahalanobis_distance),
                "threshold": threshold,
                "confidence": min(1.0, float(mahalanobis_distance) / threshold)
            }
            
        except np.linalg.LinAlgError:
            # Matriz singular, usar método alternativo
            return {"is_outlier": False, "reason": "singular_matrix"}
    
    def _calculate_distance(self, point1: Tuple[float, float], 
                          point2: Tuple[float, float]) -> float:
        """Calcula distancia usando fórmula de Haversine"""
        lat1, lon1 = point1
        lat2, lon2 = point2
        
        # Radio de la Tierra en km
        R = 6371.0
        
        # Convertir a radianes
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        # Diferencias
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        # Fórmula de Haversine
        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    def _encode_decision_type(self, decision: str) -> float:
        """Codifica tipo de decisión a valor numérico"""
        encoding = {"ahorro": 1.0, "equilibrio": 2.0, "conveniencia": 3.0}
        return encoding.get(decision, 2.0)


class SeasonalAnalyzer:
    """
    Analiza patrones estacionales para distinguir de drift real
    """
    
    def __init__(self):
        self.seasonal_patterns = self._initialize_seasonal_patterns()
    
    def _initialize_seasonal_patterns(self) -> Dict[str, Dict]:
        """Inicializa patrones estacionales conocidos"""
        return {
            "navidad": {
                "period": ("12-15", "12-31"),
                "expected_changes": {
                    "productos_premium": 0.3,
                    "frecuencia_compras": 0.5,
                    "presupuesto": 0.4,
                    "marcas_especiales": ["premium", "importadas"]
                }
            },
            "verano": {
                "period": ("12-21", "03-20"),
                "expected_changes": {
                    "productos_frescos": 0.6,
                    "ubicacion_variabilidad": 0.4,
                    "horarios_compra": "flexible",
                    "supermercados_turisticos": True
                }
            },
            "inicio_mes": {
                "period": "days_1_to_5",
                "expected_changes": {
                    "presupuesto": 0.2,
                    "compras_volumen": 0.3,
                    "productos_durables": 0.4
                }
            },
            "fin_mes": {
                "period": "days_25_to_31",
                "expected_changes": {
                    "presupuesto": -0.3,
                    "marcas_economicas": 0.5,
                    "productos_basicos": 0.4
                }
            }
        }
    
    def distinguish_seasonal_vs_drift(self, user_behavior: Dict, 
                                    current_date: datetime) -> Dict[str, Any]:
        """
        Distingue entre cambios estacionales normales y drift real del contexto
        """
        active_patterns = []
        
        # Detectar patrones estacionales activos
        for pattern_name, pattern_config in self.seasonal_patterns.items():
            if self._is_pattern_active(pattern_config["period"], current_date):
                active_patterns.append(pattern_name)
        
        # Calcular score de explicación estacional
        seasonal_explanation_score = 0.0
        
        for pattern_name in active_patterns:
            pattern = self.seasonal_patterns[pattern_name]
            behavior_match_score = self._calculate_pattern_match(
                user_behavior, 
                pattern["expected_changes"]
            )
            seasonal_explanation_score = max(seasonal_explanation_score, behavior_match_score)
        
        # Decidir tipo de cambio
        if seasonal_explanation_score > 0.7:
            return {
                "type": "seasonal_change",
                "explanation": active_patterns,
                "confidence": seasonal_explanation_score,
                "action": "adjust_expectations_temporarily"
            }
        elif seasonal_explanation_score > 0.4:
            return {
                "type": "mixed_seasonal_drift",
                "explanation": f"Partially explained by {active_patterns}",
                "confidence": seasonal_explanation_score,
                "action": "monitor_closely"
            }
        else:
            return {
                "type": "context_drift",
                "explanation": "No seasonal pattern explains this change",
                "confidence": 1.0 - seasonal_explanation_score,
                "action": "initiate_context_reset"
            }
    
    def _is_pattern_active(self, period: Union[Tuple[str, str], str], 
                          current_date: datetime) -> bool:
        """Verifica si un patrón estacional está activo"""
        if isinstance(period, tuple):
            start_str, end_str = period
            # Formato "MM-DD"
            start_month, start_day = map(int, start_str.split('-'))
            end_month, end_day = map(int, end_str.split('-'))
            
            start_date = datetime(current_date.year, start_month, start_day)
            end_date = datetime(current_date.year, end_month, end_day)
            
            # Manejar cambio de año
            if start_date > end_date:
                return current_date >= start_date or current_date <= end_date
            else:
                return start_date <= current_date <= end_date
        
        elif period.startswith("days_"):
            # Formato "days_X_to_Y"
            parts = period.split('_')
            start_day = int(parts[1])
            end_day = int(parts[3])
            
            return start_day <= current_date.day <= end_day
        
        return False
    
    def _calculate_pattern_match(self, user_behavior: Dict, 
                               expected_changes: Dict) -> float:
        """Calcula qué tan bien el comportamiento coincide con un patrón estacional"""
        match_scores = []
        
        for change_type, expected_magnitude in expected_changes.items():
            if change_type in user_behavior:
                actual_change = user_behavior[change_type]
                
                if isinstance(expected_magnitude, (int, float)):
                    similarity = 1.0 - abs(actual_change - expected_magnitude) / max(abs(expected_magnitude), 1.0)
                    match_scores.append(max(0, similarity))
                elif isinstance(expected_magnitude, list):
                    match_score = 1.0 if actual_change in expected_magnitude else 0.0
                    match_scores.append(match_score)
                elif isinstance(expected_magnitude, bool):
                    match_score = 1.0 if bool(actual_change) == expected_magnitude else 0.0
                    match_scores.append(match_score)
        
        return np.mean(match_scores) if match_scores else 0.0


class ConversationService:
    """
    Servicio principal de gestión de contexto conversacional
    
    Implementa sistema Weighted Moving Average con Contextual Anchors para:
    - Mantener contexto persistente superando limitaciones de ChatGPT
    - Detectar cambios de contexto (drift) usando múltiples algoritmos
    - Anonimizar datos para cache compartido
    - Aprender adaptativamente de las interacciones del usuario
    """
    
    def __init__(self, database_session=None, database_url: str = None):
        """
        Inicializar ConversationService
        
        Args:
            database_session: Sesión de base de datos existente (preferido)
            database_url: URL de base de datos (fallback)
        """
        if database_session is not None:
            # Usar sesión existente
            self.db_session = database_session
            self.engine = database_session.bind
            self.SessionLocal = None  # No necesario cuando usamos sesión existente
        else:
            # Crear nueva conexión
            self.database_url = database_url or "sqlite:///conversation_context.db"
            self.engine = create_engine(self.database_url)
            self.SessionLocal = sessionmaker(bind=self.engine)
            self.db_session = None
        

    def get_session(self):
        """Obtener sesión de base de datos"""
        if self.db_session is not None:
            return self.db_session
        elif self.SessionLocal is not None:
            return self.SessionLocal()
        else:
            raise Exception("No hay sesión de base de datos disponible")
    
    def close_session(self, session):
        """Cerrar sesión si fue creada por este servicio"""
        if self.SessionLocal is not None and session != self.db_session:
            session.close()
                # Componentes del sistema
        self.drift_detector = DriftDetector()
        self.seasonal_analyzer = SeasonalAnalyzer()
        self.location_hasher = LocationHasher()
        
        # Cache en memoria para sesión actual
        self.current_session_cache = {}
        
        # Configuración de anclas por defecto
        self.default_anchors_config = {
            "ubicacion_hogar": {
                "weight": 0.35,
                "stability_threshold": 0.8,
                "decay_rate": 0.02
            },
            "preferencias_precio": {
                "weight": 0.25,
                "stability_threshold": 0.7,
                "decay_rate": 0.05
            },
            "patrones_temporales": {
                "weight": 0.20,
                "stability_threshold": 0.6,
                "decay_rate": 0.08
            },
            "marcas_preferidas": {
                "weight": 0.20,
                "stability_threshold": 0.75,
                "decay_rate": 0.03
            },
            "allergies": {
                "weight": 0.15,
                "stability_threshold": 0.9,
                "decay_rate": 0.01
            },
            "dietary_restrictions": {
                "weight": 0.15,
                "stability_threshold": 0.9,
                "decay_rate": 0.01
            }
        }
        
        logger.info("ConversationService inicializado correctamente")
    
    async def process_user_interaction(self, user_id: str, interaction_data: Dict) -> Dict[str, Any]:
        """
        Procesa una nueva interacción del usuario y actualiza el contexto
        
        Args:
            user_id: Identificador único del usuario
            interaction_data: Datos de la interacción (productos, ubicación, decisión, etc.)
        
        Returns:
            Dict con contexto actualizado y recomendaciones
        """
        try:
            # Crear objeto de interacción
            interaction = UserInteraction(
                interaction_id=str(uuid.uuid4()),
                user_id=user_id,
                timestamp=datetime.now(),
                productos=interaction_data.get("productos", []),
                ubicacion=tuple(interaction_data.get("ubicacion", [0.0, 0.0])),
                decision_tomada=interaction_data.get("decision_tomada", "equilibrio"),
                supermercados_visitados=interaction_data.get("supermercados_visitados", []),
                satisfaccion=interaction_data.get("satisfaccion", 3.0),
                context_data=interaction_data.get("context_data", {})
            )
            
            # Cargar o crear perfil de usuario
            user_profile = await self._load_or_create_user_profile(user_id)
            
            # Detectar cambios de contexto
            drift_result = await self._detect_context_drift(interaction, user_profile)
            
            # Actualizar contexto según resultado de detección
            updated_context = await self._update_user_context(
                user_profile, interaction, drift_result
            )
            
            # Guardar interacción en base de datos
            await self._save_interaction(interaction)
            
            # Actualizar cache anónimo si es apropiado
            await self._update_anonymous_cache(interaction)
            
            # Generar respuesta contextual
            response = await self._generate_contextual_response(
                updated_context, interaction, drift_result
            )
            
            logger.info(f"Interacción procesada exitosamente para usuario {user_id}")
            
            return response
            
        except Exception as e:
            logger.error(f"Error procesando interacción para usuario {user_id}: {str(e)}")
            raise
    
    async def _load_or_create_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Carga perfil existente o crea uno nuevo"""
        async with self.SessionLocal() as session:
            # Buscar usuario existente
            query = text("""
                SELECT user_id, session_id, created_at, expires_at, is_temporary, privacy_consent
                FROM usuarios WHERE user_id = :user_id OR session_id = :user_id
            """)
            
            result = await session.execute(query, {"user_id": user_id})
            user_row = result.fetchone()
            
            if user_row:
                # Usuario existente - cargar contexto completo
                return await self._load_full_user_context(user_row.user_id)
            else:
                # Usuario nuevo - crear perfil
                return await self._create_new_user_profile(user_id)
    
    async def _load_full_user_context(self, user_id: str) -> Dict[str, Any]:
        """Carga el contexto completo del usuario desde la base de datos"""
        async with self.SessionLocal() as session:
            # Cargar anclas contextuales
            anchors_query = text("""
                SELECT anchor_name, anchor_value, confidence_score, 
                       stability_threshold, last_updated, update_count
                FROM contextual_anchors 
                WHERE user_id = :user_id AND confidence_score > 0.1
                ORDER BY confidence_score DESC
            """)
            
            anchors_result = await session.execute(anchors_query, {"user_id": user_id})
            anchors_data = anchors_result.fetchall()
            
            # Reconstruir anclas
            anchors = {}
            for row in anchors_data:
                config = self.default_anchors_config.get(row.anchor_name, {})
                anchors[row.anchor_name] = ContextualAnchor(
                    name=row.anchor_name,
                    weight=config.get("weight", 0.25),
                    stability_threshold=config.get("stability_threshold", 0.7),
                    decay_rate=config.get("decay_rate", 0.05),
                    current_value=json.loads(row.anchor_value) if row.anchor_value else None,
                    confidence=float(row.confidence_score),
                    last_updated=row.last_updated,
                    update_count=row.update_count
                )
            
            # Cargar interacciones recientes
            interactions_query = text("""
                SELECT interaction_data, timestamp
                FROM user_interactions 
                WHERE user_id = :user_id 
                ORDER BY timestamp DESC 
                LIMIT 50
            """)
            
            interactions_result = await session.execute(interactions_query, {"user_id": user_id})
            recent_interactions = [
                {
                    "data": json.loads(row.interaction_data),
                    "timestamp": row.timestamp
                }
                for row in interactions_result.fetchall()
            ]
            
            return {
                "user_id": user_id,
                "anchors": anchors,
                "recent_interactions": recent_interactions,
                "moving_averages": self._initialize_moving_averages(),
                "context_history": []
            }
    
    async def _create_new_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Crea un nuevo perfil de usuario"""
        async with self.SessionLocal() as session:
            # Crear registro de usuario
            user_insert = text("""
                INSERT INTO usuarios (user_id, session_id, created_at, expires_at, is_temporary)
                VALUES (:user_id, :session_id, :created_at, :expires_at, :is_temporary)
            """)
            
            is_temporary = not user_id.startswith("persistent_")
            expires_at = datetime.now() + timedelta(hours=12) if is_temporary else None
            
            await session.execute(user_insert, {
                "user_id": user_id,
                "session_id": user_id,
                "created_at": datetime.now(),
                "expires_at": expires_at,
                "is_temporary": is_temporary
            })
            
            # Inicializar anclas por defecto
            anchors = {}
            for anchor_name, config in self.default_anchors_config.items():
                anchors[anchor_name] = ContextualAnchor(
                    name=anchor_name,
                    weight=config["weight"],
                    stability_threshold=config["stability_threshold"],
                    decay_rate=config["decay_rate"]
                )
            
            await session.commit()
            
            return {
                "user_id": user_id,
                "anchors": anchors,
                "recent_interactions": [],
                "moving_averages": self._initialize_moving_averages(),
                "context_history": []
            }
    
    def _initialize_moving_averages(self) -> Dict[str, WeightedMovingAverage]:
        """Inicializa sistemas de promedio móvil para diferentes métricas"""
        return {
            "satisfaction": WeightedMovingAverage(window_size=20, alpha=0.3),
            "decision_consistency": WeightedMovingAverage(window_size=15, alpha=0.4),
            "location_stability": WeightedMovingAverage(window_size=25, alpha=0.2),
            "temporal_patterns": WeightedMovingAverage(window_size=30, alpha=0.25)
        }
    
    async def _detect_context_drift(self, interaction: UserInteraction, 
                                  user_profile: Dict[str, Any]) -> DriftDetectionResult:
        """
        Detecta cambios de contexto usando múltiples algoritmos
        """
        drift_signals = {}
        anchors = user_profile["anchors"]
        recent_interactions = user_profile["recent_interactions"]
        
        # 1. Análisis de Anclas Contextuales
        for anchor_name, anchor in anchors.items():
            if anchor.current_value is not None:
                deviation = self._calculate_anchor_deviation(interaction, anchor)
                if deviation > anchor.stability_threshold:
                    drift_signals[anchor_name] = {
                        "severity": deviation,
                        "confidence": min(1.0, deviation / anchor.stability_threshold),
                        "type": f"{anchor_name}_drift"
                    }
        
        # 2. Test CUSUM para decisiones
        if len(recent_interactions) >= 5:
            recent_decisions = [
                i["data"].get("decision_tomada", "equilibrio") 
                for i in recent_interactions[-10:]
            ]
            cusum_result = self.drift_detector.cusum_test(recent_decisions, interaction.decision_tomada)
            
            if cusum_result["change_detected"]:
                drift_signals["decision_pattern"] = {
                    "severity": cusum_result["magnitude"],
                    "confidence": cusum_result["confidence"],
                    "type": "preference_shift"
                }
        
        # 3. Análisis de Outliers Multivariados
        if len(recent_interactions) >= 10:
            historical_interactions = self._convert_to_interaction_objects(recent_interactions)
            home_location = self._extract_home_location(anchors)
            
            outlier_result = self.drift_detector.detect_multivariate_outliers(
                interaction, historical_interactions, home_location
            )
            
            if outlier_result.get("is_outlier", False):
                drift_signals["multivariate_outlier"] = {
                    "severity": outlier_result["confidence"],
                    "confidence": outlier_result["confidence"],
                    "type": "erratic_behavior"
                }
        
        # 4. Análisis Estacional
        user_behavior = self._extract_behavior_metrics(interaction, recent_interactions)
        seasonal_result = self.seasonal_analyzer.distinguish_seasonal_vs_drift(
            user_behavior, interaction.timestamp
        )
        
        # Evaluar significancia del drift
        return self._evaluate_drift_significance(drift_signals, seasonal_result)
    
    def _calculate_anchor_deviation(self, interaction: UserInteraction, 
                                  anchor: ContextualAnchor) -> float:
        """Calcula desviación de una interacción respecto a un ancla"""
        if anchor.current_value is None:
            return 0.0
        
        if anchor.name == "ubicacion_hogar":
            current_location = anchor.current_value
            if isinstance(current_location, (list, tuple)) and len(current_location) == 2:
                distance = self.drift_detector._calculate_distance(
                    tuple(current_location), interaction.ubicacion
                )
                return min(1.0, distance / 10.0)  # Normalizar a 10km máximo
        
        elif anchor.name == "preferencias_precio":
            current_pref = anchor.current_value.get("prioridad", "equilibrio")
            decision_similarity = 1.0 if current_pref == interaction.decision_tomada else 0.5
            return 1.0 - decision_similarity
        
        elif anchor.name == "patrones_temporales":
            current_patterns = anchor.current_value
            if "horario_preferido" in current_patterns:
                preferred_hour = current_patterns["horario_preferido"]
                hour_diff = abs(interaction.timestamp.hour - preferred_hour)
                return min(1.0, hour_diff / 12.0)  # Normalizar a 12 horas máximo
        
        elif anchor.name == "marcas_preferidas":
            preferred_brands = set(anchor.current_value.get("marcas", []))
            interaction_brands = set()
            for producto in interaction.productos:
                # Extraer marca del nombre del producto (simplificado)
                for brand in ["soprole", "ideal", "carozzi", "lider", "jumbo"]:
                    if brand.lower() in producto.lower():
                        interaction_brands.add(brand)
            
            if preferred_brands and interaction_brands:
                overlap = len(preferred_brands & interaction_brands)
                return 1.0 - (overlap / len(preferred_brands))
        
        return 0.0
    
    def _convert_to_interaction_objects(self, interactions_data: List[Dict]) -> List[UserInteraction]:
        """Convierte datos de interacciones a objetos UserInteraction"""
        interactions = []
        for item in interactions_data:
            data = item["data"]
            interaction = UserInteraction(
                interaction_id=data.get("interaction_id", str(uuid.uuid4())),
                user_id=data.get("user_id", ""),
                timestamp=item["timestamp"],
                productos=data.get("productos", []),
                ubicacion=tuple(data.get("ubicacion", [0.0, 0.0])),
                decision_tomada=data.get("decision_tomada", "equilibrio"),
                supermercados_visitados=data.get("supermercados_visitados", []),
                satisfaccion=data.get("satisfaccion", 3.0)
            )
            interactions.append(interaction)
        return interactions
    
    def _extract_home_location(self, anchors: Dict[str, ContextualAnchor]) -> Tuple[float, float]:
        """Extrae ubicación del hogar de las anclas"""
        home_anchor = anchors.get("ubicacion_hogar")
        if home_anchor and home_anchor.current_value:
            location = home_anchor.current_value
            if isinstance(location, (list, tuple)) and len(location) == 2:
                return tuple(location)
        return (0.0, 0.0)
    
    def _extract_behavior_metrics(self, interaction: UserInteraction, 
                                recent_interactions: List[Dict]) -> Dict[str, Any]:
        """Extrae métricas de comportamiento para análisis estacional"""
        if not recent_interactions:
            return {}
        
        # Calcular métricas de comportamiento reciente
        recent_satisfactions = [i["data"].get("satisfaccion", 3.0) for i in recent_interactions[-5:]]
        recent_decisions = [i["data"].get("decision_tomada", "equilibrio") for i in recent_interactions[-5:]]
        
        return {
            "satisfaction_trend": np.mean(recent_satisfactions) - 3.0,  # Desviación de neutral
            "decision_consistency": len(set(recent_decisions)) / len(recent_decisions),
            "productos_premium": self._count_premium_products(interaction.productos),
            "frecuencia_compras": len(recent_interactions) / 30,  # Compras por día
            "presupuesto_estimado": len(interaction.productos) * 2000  # Estimación simple
        }
    
    def _count_premium_products(self, productos: List[str]) -> float:
        """Cuenta productos premium en la lista"""
        premium_keywords = ["premium", "gourmet", "importado", "orgánico"]
        premium_count = 0
        
        for producto in productos:
            if any(keyword in producto.lower() for keyword in premium_keywords):
                premium_count += 1
        
        return premium_count / len(productos) if productos else 0.0
    
    def _evaluate_drift_significance(self, drift_signals: Dict[str, Dict], 
                                   seasonal_result: Dict[str, Any]) -> DriftDetectionResult:
        """Evalúa la significancia del drift detectado"""
        
        # Si es cambio estacional, no es drift real
        if seasonal_result["type"] == "seasonal_change":
            return DriftDetectionResult(
                has_drift=False,
                drift_type=ChangeType.SEASONAL_CHANGE,
                confidence=seasonal_result["confidence"],
                affected_anchors=[],
                detection_algorithm=DriftDetectionAlgorithm.VARIANCE_TEST,
                magnitude=0.0,
                recommended_action="adjust_seasonal_expectations"
            )
        
        # Evaluar drift real
        if len(drift_signals) >= 2:  # Al menos 2 señales de drift
            # Calcular confianza promedio ponderada
            total_weight = 0.0
            weighted_confidence = 0.0
            affected_anchors = []
            max_severity = 0.0
            
            for signal_name, signal_data in drift_signals.items():
                weight = 1.0  # Peso igual por ahora, se puede sofisticar
                confidence = signal_data["confidence"]
                severity = signal_data["severity"]
                
                weighted_confidence += confidence * weight
                total_weight += weight
                affected_anchors.append(signal_name)
                max_severity = max(max_severity, severity)
            
            final_confidence = weighted_confidence / total_weight if total_weight > 0 else 0.0
            
            # Determinar tipo de drift predominante
            drift_types = [signal["type"] for signal in drift_signals.values()]
            most_common_type = max(set(drift_types), key=drift_types.count)
            
            # Mapear a enum
            drift_type_mapping = {
                "ubicacion_hogar_drift": ChangeType.LOCATION_DRIFT,
                "preferencias_precio_drift": ChangeType.PREFERENCE_SHIFT,
                "patrones_temporales_drift": ChangeType.TEMPORAL_CHANGE,
                "preference_shift": ChangeType.PREFERENCE_SHIFT,
                "erratic_behavior": ChangeType.ERRATIC_BEHAVIOR
            }
            
            drift_type = drift_type_mapping.get(most_common_type, ChangeType.PREFERENCE_SHIFT)
            
            # Determinar acción recomendada
            if final_confidence > 0.8 and max_severity > 0.7:
                recommended_action = "immediate_context_reset"
            elif final_confidence > 0.6:
                recommended_action = "gradual_adaptation"
            else:
                recommended_action = "increase_monitoring"
            
            return DriftDetectionResult(
                has_drift=True,
                drift_type=drift_type,
                confidence=final_confidence,
                affected_anchors=affected_anchors,
                detection_algorithm=DriftDetectionAlgorithm.CUSUM,  # Algoritmo principal usado
                magnitude=max_severity,
                recommended_action=recommended_action
            )
        
        # No hay drift significativo
        return DriftDetectionResult(
            has_drift=False,
            drift_type=None,
            confidence=0.0,
            affected_anchors=[],
            detection_algorithm=DriftDetectionAlgorithm.CUSUM,
            magnitude=0.0,
            recommended_action="continue_normal_operation"
        )
    
    async def _update_user_context(self, user_profile: Dict[str, Any], 
                                 interaction: UserInteraction,
                                 drift_result: DriftDetectionResult) -> Dict[str, Any]:
        """Actualiza el contexto del usuario basado en la nueva interacción y drift detectado"""
        
        anchors = user_profile["anchors"]
        moving_averages = user_profile["moving_averages"]
        
        # Actualizar promedios móviles
        moving_averages["satisfaction"].update(interaction.satisfaccion, interaction.timestamp)
        
        # Codificar decisión para promedio móvil
        decision_encoding = {"ahorro": 1.0, "equilibrio": 2.0, "conveniencia": 3.0}
        decision_value = decision_encoding.get(interaction.decision_tomada, 2.0)
        moving_averages["decision_consistency"].update(decision_value, interaction.timestamp)
        
        # Actualizar anclas según resultado de drift
        if drift_result.has_drift:
            await self._handle_context_drift(anchors, interaction, drift_result)
        else:
            await self._update_anchors_normal(anchors, interaction)
        
        # Guardar anclas actualizadas en base de datos
        await self._save_updated_anchors(user_profile["user_id"], anchors)
        
        # Registrar cambio de contexto si es necesario
        if drift_result.has_drift:
            await self._log_context_change(user_profile["user_id"], drift_result)
        
        return {
            "user_id": user_profile["user_id"],
            "anchors": anchors,
            "moving_averages": moving_averages,
            "drift_detected": drift_result.has_drift,
            "drift_result": drift_result,
            "updated_at": datetime.now()
        }
    
    async def _handle_context_drift(self, anchors: Dict[str, ContextualAnchor],
                                  interaction: UserInteraction,
                                  drift_result: DriftDetectionResult):
        """Maneja el drift de contexto actualizando anclas afectadas"""
        
        # Estrategias de respuesta según tipo de drift
        response_strategies = {
            ChangeType.LOCATION_DRIFT: {
                "anchor_reset_percentage": 0.8,
                "learning_rate_multiplier": 2.0,
                "confidence_threshold": 0.3
            },
            ChangeType.PREFERENCE_SHIFT: {
                "anchor_reset_percentage": 0.6,
                "learning_rate_multiplier": 1.5,
                "confidence_threshold": 0.5
            },
            ChangeType.TEMPORAL_CHANGE: {
                "anchor_reset_percentage": 0.4,
                "learning_rate_multiplier": 1.3,
                "confidence_threshold": 0.6
            },
            ChangeType.ERRATIC_BEHAVIOR: {
                "anchor_reset_percentage": 0.1,
                "learning_rate_multiplier": 0.8,
                "confidence_threshold": 0.8
            }
        }
        
        strategy = response_strategies.get(drift_result.drift_type, response_strategies[ChangeType.PREFERENCE_SHIFT])
        
        # Actualizar anclas afectadas
        for anchor_name in drift_result.affected_anchors:
            if anchor_name in anchors:
                anchor = anchors[anchor_name]
                
                # Calcular nuevo valor mezclando anterior con nuevo
                new_value = self._extract_anchor_value_from_interaction(interaction, anchor_name)
                if new_value is not None:
                    blend_ratio = strategy["anchor_reset_percentage"]
                    
                    if anchor.current_value is not None:
                        # Mezclar valores
                        anchor.current_value = self._blend_anchor_values(
                            anchor.current_value, new_value, blend_ratio
                        )
                    else:
                        # Primer valor
                        anchor.current_value = new_value
                    
                    # Ajustar confianza
                    anchor.confidence = strategy["confidence_threshold"]
                    anchor.last_updated = datetime.now()
                    anchor.update_count += 1
                    
                    # Registrar en historial
                    anchor.update_history.append({
                        "timestamp": datetime.now(),
                        "trigger": "drift_detection",
                        "drift_type": drift_result.drift_type.value,
                        "confidence_before": anchor.confidence,
                        "value_before": anchor.current_value
                    })
        
        logger.info(f"Contexto actualizado por drift: {drift_result.drift_type.value}")
    
    async def _update_anchors_normal(self, anchors: Dict[str, ContextualAnchor],
                                   interaction: UserInteraction):
        """Actualiza anclas en operación normal (sin drift)"""
        
        for anchor_name, anchor in anchors.items():
            new_value = self._extract_anchor_value_from_interaction(interaction, anchor_name)
            
            if new_value is not None:
                if anchor.current_value is not None:
                    # Actualización gradual usando decay rate
                    anchor.current_value = self._blend_anchor_values(
                        anchor.current_value, new_value, anchor.decay_rate
                    )
                    
                    # Aumentar confianza gradualmente
                    anchor.confidence = min(1.0, anchor.confidence + 0.01)
                else:
                    # Primer valor
                    anchor.current_value = new_value
                    anchor.confidence = 0.5
                
                anchor.last_updated = datetime.now()
                anchor.update_count += 1
    
    def _extract_anchor_value_from_interaction(self, interaction: UserInteraction, 
                                             anchor_name: str) -> Any:
        """Extrae valor de ancla de una interacción"""
        
        if anchor_name == "ubicacion_hogar":
            return list(interaction.ubicacion)
        
        elif anchor_name == "preferencias_precio":
            return {
                "prioridad": interaction.decision_tomada,
                "satisfaccion_promedio": interaction.satisfaccion
            }
        
        elif anchor_name == "patrones_temporales":
            return {
                "horario_preferido": interaction.timestamp.hour,
                "dia_semana_preferido": interaction.timestamp.weekday(),
                "frecuencia_semanal": 1.0  # Se calculará con más datos
            }
        
        elif anchor_name == "marcas_preferidas":
            # Extraer marcas de los productos
            marcas = []
            for producto in interaction.productos:
                for marca in ["soprole", "ideal", "carozzi", "lider", "jumbo", "tottus"]:
                    if marca.lower() in producto.lower():
                        marcas.append(marca)
            
            return {
                "marcas": list(set(marcas)),
                "supermercados": interaction.supermercados_visitados
            }
        
        return None
    
    def _blend_anchor_values(self, old_value: Any, new_value: Any, blend_ratio: float) -> Any:
        """Mezcla valores de ancla según ratio de blend"""
        
        if isinstance(old_value, dict) and isinstance(new_value, dict):
            # Mezclar diccionarios
            blended = old_value.copy()
            for key, new_val in new_value.items():
                if key in blended:
                    if isinstance(new_val, (int, float)) and isinstance(blended[key], (int, float)):
                        blended[key] = blended[key] * (1 - blend_ratio) + new_val * blend_ratio
                    elif isinstance(new_val, list) and isinstance(blended[key], list):
                        # Mezclar listas manteniendo elementos únicos
                        combined = list(set(blended[key] + new_val))
                        blended[key] = combined
                    else:
                        blended[key] = new_val if blend_ratio > 0.5 else blended[key]
                else:
                    blended[key] = new_val
            return blended
        
        elif isinstance(old_value, list) and isinstance(new_value, list):
            # Mezclar listas
            if blend_ratio > 0.5:
                return list(set(old_value + new_value))
            else:
                return old_value
        
        elif isinstance(old_value, (int, float)) and isinstance(new_value, (int, float)):
            # Mezclar valores numéricos
            return old_value * (1 - blend_ratio) + new_value * blend_ratio
        
        else:
            # Para otros tipos, usar nuevo valor si blend_ratio > 0.5
            return new_value if blend_ratio > 0.5 else old_value
    
    async def _save_updated_anchors(self, user_id: str, anchors: Dict[str, ContextualAnchor]):
        """Guarda anclas actualizadas en la base de datos"""
        async with self.SessionLocal() as session:
            for anchor_name, anchor in anchors.items():
                if anchor.current_value is not None:
                    # Upsert anchor
                    upsert_query = text("""
                        INSERT INTO contextual_anchors 
                        (user_id, anchor_name, anchor_value, confidence_score, 
                         stability_threshold, last_updated, update_count)
                        VALUES (:user_id, :anchor_name, :anchor_value, :confidence_score,
                                :stability_threshold, :last_updated, :update_count)
                        ON CONFLICT (user_id, anchor_name) 
                        DO UPDATE SET
                            anchor_value = EXCLUDED.anchor_value,
                            confidence_score = EXCLUDED.confidence_score,
                            last_updated = EXCLUDED.last_updated,
                            update_count = EXCLUDED.update_count
                    """)
                    
                    await session.execute(upsert_query, {
                        "user_id": user_id,
                        "anchor_name": anchor_name,
                        "anchor_value": json.dumps(anchor.current_value),
                        "confidence_score": anchor.confidence,
                        "stability_threshold": anchor.stability_threshold,
                        "last_updated": anchor.last_updated,
                        "update_count": anchor.update_count
                    })
            
            await session.commit()
    
    async def _save_interaction(self, interaction: UserInteraction):
        """Guarda interacción en la base de datos"""
        async with self.SessionLocal() as session:
            # Crear hash de ubicación para anonimización
            location_hash_data = self.location_hasher.create_location_hash(
                interaction.ubicacion[0], interaction.ubicacion[1]
            )
            
            # Crear hash de interacción para cache
            interaction_hash = self._create_interaction_hash(interaction)
            
            # Guardar interacción
            insert_query = text("""
                INSERT INTO user_interactions 
                (interaction_id, user_id, interaction_data, timestamp, interaction_hash)
                VALUES (:interaction_id, :user_id, :interaction_data, :timestamp, :interaction_hash)
            """)
            
            interaction_data = {
                "productos": interaction.productos,
                "ubicacion": interaction.ubicacion,
                "decision_tomada": interaction.decision_tomada,
                "supermercados_visitados": interaction.supermercados_visitados,
                "satisfaccion": interaction.satisfaccion,
                "context_data": interaction.context_data,
                "location_hash": location_hash_data["hash"],
                "region_code": location_hash_data["region_code"]
            }
            
            await session.execute(insert_query, {
                "interaction_id": interaction.interaction_id,
                "user_id": interaction.user_id,
                "interaction_data": json.dumps(interaction_data),
                "timestamp": interaction.timestamp,
                "interaction_hash": interaction_hash
            })
            
            await session.commit()
    
    def _create_interaction_hash(self, interaction: UserInteraction) -> str:
        """Crea hash de interacción para cache anónimo"""
        # Normalizar productos a categorías
        product_categories = []
        for producto in interaction.productos:
            category = self._classify_product_category(producto)
            product_categories.append(category)
        
        # Crear hash basado en datos anonimizados
        hash_data = {
            "categories": sorted(product_categories),
            "decision_type": interaction.decision_tomada,
            "region": self.location_hasher.create_location_hash(
                interaction.ubicacion[0], interaction.ubicacion[1], "medium"
            )["region_code"],
            "satisfaction_bucket": self._bucket_satisfaction(interaction.satisfaccion)
        }
        
        hash_string = json.dumps(hash_data, sort_keys=True)
        return hashlib.sha256(hash_string.encode()).hexdigest()[:16]
    
    def _classify_product_category(self, producto_name: str) -> str:
        """Clasifica productos en categorías generales"""
        categories_map = {
            "lacteos": ["leche", "yogurt", "queso", "mantequilla"],
            "panaderia": ["pan", "hallulla", "marraqueta", "dobladitas"],
            "carnes": ["pollo", "carne", "pescado", "cerdo"],
            "frutas_verduras": ["manzana", "platano", "lechuga", "tomate"],
            "abarrotes": ["arroz", "fideos", "aceite", "azucar"],
            "limpieza": ["detergente", "shampoo", "papel"],
            "bebidas": ["agua", "jugo", "bebida", "cerveza"]
        }
        
        producto_lower = producto_name.lower()
        
        for category, keywords in categories_map.items():
            if any(keyword in producto_lower for keyword in keywords):
                return category
        
        return "otros"
    
    def _bucket_satisfaction(self, satisfaction_score: float) -> str:
        """Agrupa scores de satisfacción en buckets"""
        if satisfaction_score >= 4.5:
            return "very_high"
        elif satisfaction_score >= 3.5:
            return "high"
        elif satisfaction_score >= 2.5:
            return "medium"
        elif satisfaction_score >= 1.5:
            return "low"
        else:
            return "very_low"
    
    async def _update_anonymous_cache(self, interaction: UserInteraction):
        """Actualiza cache anónimo con la interacción"""
        # Solo actualizar cache si la interacción es suficientemente común
        interaction_hash = self._create_interaction_hash(interaction)
        
        async with self.SessionLocal() as session:
            # Verificar si ya existe en cache
            check_query = text("""
                SELECT cache_id, usage_count FROM anonymous_cache 
                WHERE query_hash = :query_hash
            """)
            
            result = await session.execute(check_query, {"query_hash": interaction_hash})
            existing = result.fetchone()
            
            if existing:
                # Incrementar contador de uso
                update_query = text("""
                    UPDATE anonymous_cache 
                    SET usage_count = usage_count + 1,
                        expires_at = :new_expires_at
                    WHERE cache_id = :cache_id
                """)
                
                await session.execute(update_query, {
                    "cache_id": existing.cache_id,
                    "new_expires_at": datetime.now() + timedelta(days=30)
                })
            else:
                # Crear nueva entrada en cache
                location_data = self.location_hasher.create_location_hash(
                    interaction.ubicacion[0], interaction.ubicacion[1]
                )
                
                insert_query = text("""
                    INSERT INTO anonymous_cache 
                    (query_hash, region_code, product_categories, optimization_params, 
                     result_data, usage_count, created_at, expires_at)
                    VALUES (:query_hash, :region_code, :product_categories, 
                            :optimization_params, :result_data, :usage_count, 
                            :created_at, :expires_at)
                """)
                
                product_categories = [
                    self._classify_product_category(p) for p in interaction.productos
                ]
                
                await session.execute(insert_query, {
                    "query_hash": interaction_hash,
                    "region_code": location_data["region_code"],
                    "product_categories": json.dumps(product_categories),
                    "optimization_params": json.dumps({
                        "decision_type": interaction.decision_tomada,
                        "satisfaction_bucket": self._bucket_satisfaction(interaction.satisfaccion)
                    }),
                    "result_data": json.dumps({
                        "supermercados_sugeridos": interaction.supermercados_visitados,
                        "satisfaction_outcome": self._bucket_satisfaction(interaction.satisfaccion)
                    }),
                    "usage_count": 1,
                    "created_at": datetime.now(),
                    "expires_at": datetime.now() + timedelta(days=30)
                })
            
            await session.commit()
    
    async def _log_context_change(self, user_id: str, drift_result: DriftDetectionResult):
        """Registra cambio de contexto en la base de datos"""
        async with self.SessionLocal() as session:
            insert_query = text("""
                INSERT INTO context_changes 
                (user_id, change_type, detection_algorithm, change_magnitude, 
                 confidence_score, affected_anchors, detection_timestamp, was_confirmed)
                VALUES (:user_id, :change_type, :detection_algorithm, :change_magnitude,
                        :confidence_score, :affected_anchors, :detection_timestamp, :was_confirmed)
            """)
            
            await session.execute(insert_query, {
                "user_id": user_id,
                "change_type": drift_result.drift_type.value if drift_result.drift_type else "unknown",
                "detection_algorithm": drift_result.detection_algorithm.value,
                "change_magnitude": drift_result.magnitude,
                "confidence_score": drift_result.confidence,
                "affected_anchors": json.dumps(drift_result.affected_anchors),
                "detection_timestamp": datetime.now(),
                "was_confirmed": None  # Se actualizará con feedback del usuario
            })
            
            await session.commit()
    
    async def _generate_contextual_response(self, updated_context: Dict[str, Any],
                                          interaction: UserInteraction,
                                          drift_result: DriftDetectionResult) -> Dict[str, Any]:
        """Genera respuesta contextual para el GPT"""
        
        response = {
            "user_id": updated_context["user_id"],
            "context_summary": self._generate_context_summary(updated_context),
            "recommendations": self._generate_recommendations(updated_context, interaction),
            "drift_info": {
                "drift_detected": drift_result.has_drift,
                "drift_type": drift_result.drift_type.value if drift_result.drift_type else None,
                "confidence": drift_result.confidence,
                "recommended_action": drift_result.recommended_action
            },
            "conversation_guidance": self._generate_conversation_guidance(updated_context, drift_result),
            "timestamp": datetime.now().isoformat()
        }
        
        return response
    
    def _generate_context_summary(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Genera resumen del contexto actual del usuario"""
        anchors = context["anchors"]
        
        summary = {
            "user_profile_strength": self._calculate_profile_strength(anchors),
            "primary_location": self._extract_primary_location(anchors),
            "preference_profile": self._extract_preference_profile(anchors),
            "behavioral_patterns": self._extract_behavioral_patterns(anchors),
            "confidence_level": self._calculate_overall_confidence(anchors)
        }
        
        return summary
    
    def _calculate_profile_strength(self, anchors: Dict[str, ContextualAnchor]) -> str:
        """Calcula fortaleza del perfil del usuario"""
        total_confidence = sum(anchor.confidence for anchor in anchors.values())
        avg_confidence = total_confidence / len(anchors) if anchors else 0.0
        
        if avg_confidence > 0.8:
            return "strong"
        elif avg_confidence > 0.5:
            return "moderate"
        else:
            return "weak"
    
    def _extract_primary_location(self, anchors: Dict[str, ContextualAnchor]) -> Optional[Dict]:
        """Extrae ubicación principal del usuario"""
        location_anchor = anchors.get("ubicacion_hogar")
        if location_anchor and location_anchor.current_value and location_anchor.confidence > 0.3:
            location = location_anchor.current_value
            if isinstance(location, (list, tuple)) and len(location) == 2:
                # Anonimizar ubicación para respuesta
                location_hash = self.location_hasher.create_location_hash(
                    location[0], location[1], "low"
                )
                return {
                    "region": location_hash["region_code"],
                    "confidence": location_anchor.confidence
                }
        return None
    
    def _extract_preference_profile(self, anchors: Dict[str, ContextualAnchor]) -> Dict[str, Any]:
        """Extrae perfil de preferencias del usuario"""
        pref_anchor = anchors.get("preferencias_precio")
        allergy_anchor = anchors.get("allergies")
        dietary_anchor = anchors.get("dietary_restrictions")

        prefs = {
            "optimization_priority": "equilibrio",
            "satisfaction_level": 3.0,
            "allergies": allergy_anchor.current_value if allergy_anchor and allergy_anchor.current_value else [],
            "dietary_restrictions": dietary_anchor.current_value if dietary_anchor and dietary_anchor.current_value else [],
            "confidence": 0.0,
        }

        if pref_anchor and pref_anchor.current_value and pref_anchor.confidence > 0.3:
            pref_values = pref_anchor.current_value
            prefs.update({
                "optimization_priority": pref_values.get("prioridad", "equilibrio"),
                "satisfaction_level": pref_values.get("satisfaccion_promedio", 3.0),
                "confidence": pref_anchor.confidence,
            })

        return prefs
    
    def _extract_behavioral_patterns(self, anchors: Dict[str, ContextualAnchor]) -> Dict[str, Any]:
        """Extrae patrones de comportamiento del usuario"""
        temporal_anchor = anchors.get("patrones_temporales")
        brands_anchor = anchors.get("marcas_preferidas")
        
        patterns = {}
        
        if temporal_anchor and temporal_anchor.current_value and temporal_anchor.confidence > 0.3:
            temporal_data = temporal_anchor.current_value
            patterns["temporal"] = {
                "preferred_hour": temporal_data.get("horario_preferido"),
                "preferred_weekday": temporal_data.get("dia_semana_preferido"),
                "confidence": temporal_anchor.confidence
            }
        
        if brands_anchor and brands_anchor.current_value and brands_anchor.confidence > 0.3:
            brands_data = brands_anchor.current_value
            patterns["brands"] = {
                "preferred_brands": brands_data.get("marcas", []),
                "preferred_stores": brands_data.get("supermercados", []),
                "confidence": brands_anchor.confidence
            }
        
        return patterns
    
    def _calculate_overall_confidence(self, anchors: Dict[str, ContextualAnchor]) -> float:
        """Calcula confianza general del perfil"""
        if not anchors:
            return 0.0
        
        weighted_confidence = 0.0
        total_weight = 0.0
        
        for anchor in anchors.values():
            weighted_confidence += anchor.confidence * anchor.weight
            total_weight += anchor.weight
        
        return weighted_confidence / total_weight if total_weight > 0 else 0.0
    
    def _generate_recommendations(self, context: Dict[str, Any], 
                                interaction: UserInteraction) -> List[Dict[str, Any]]:
        """Genera recomendaciones basadas en el contexto"""
        recommendations = []
        anchors = context["anchors"]
        
        # Recomendación basada en ubicación
        location_anchor = anchors.get("ubicacion_hogar")
        if location_anchor and location_anchor.confidence > 0.5:
            recommendations.append({
                "type": "location_based",
                "message": "Basado en tu ubicación habitual, te sugiero considerar supermercados cercanos",
                "confidence": location_anchor.confidence
            })
        
        # Recomendación basada en preferencias
        pref_anchor = anchors.get("preferencias_precio")
        if pref_anchor and pref_anchor.confidence > 0.5:
            pref_data = pref_anchor.current_value
            priority = pref_data.get("prioridad", "equilibrio")
            
            if priority == "ahorro":
                recommendations.append({
                    "type": "optimization_preference",
                    "message": "Dado que priorizas el ahorro, te sugiero comparar precios en múltiples tiendas",
                    "confidence": pref_anchor.confidence
                })
            elif priority == "conveniencia":
                recommendations.append({
                    "type": "optimization_preference", 
                    "message": "Como prefieres la conveniencia, te sugiero una tienda que tenga la mayoría de productos",
                    "confidence": pref_anchor.confidence
                })
        
        # Recomendación basada en marcas
        brands_anchor = anchors.get("marcas_preferidas")
        if brands_anchor and brands_anchor.confidence > 0.4:
            brands_data = brands_anchor.current_value
            preferred_stores = brands_data.get("supermercados", [])
            
            if preferred_stores:
                recommendations.append({
                    "type": "store_preference",
                    "message": f"Considerando tu historial, podrías preferir: {', '.join(preferred_stores[:2])}",
                    "confidence": brands_anchor.confidence
                })
        
        return recommendations
    
    def _generate_conversation_guidance(self, context: Dict[str, Any], 
                                      drift_result: DriftDetectionResult) -> Dict[str, Any]:
        """Genera guía para la conversación del GPT"""
        
        guidance = {
            "conversation_tone": "helpful",
            "personalization_level": self._calculate_personalization_level(context),
            "suggested_questions": [],
            "context_actions": []
        }
        
        # Ajustar según drift detectado
        if drift_result.has_drift:
            if drift_result.drift_type == ChangeType.LOCATION_DRIFT:
                guidance["suggested_questions"].append(
                    "¿Te has mudado recientemente o estás en una ubicación diferente?"
                )
                guidance["context_actions"].append("confirm_location_change")
            
            elif drift_result.drift_type == ChangeType.PREFERENCE_SHIFT:
                guidance["suggested_questions"].append(
                    "¿Han cambiado tus prioridades de compra últimamente?"
                )
                guidance["context_actions"].append("confirm_preference_change")
            
            guidance["conversation_tone"] = "adaptive"
        
        # Sugerir preguntas según fortaleza del perfil
        profile_strength = self._calculate_profile_strength(context["anchors"])
        
        if profile_strength == "weak":
            guidance["suggested_questions"].extend([
                "¿Cuáles son tus supermercados preferidos?",
                "¿Qué es más importante para ti: ahorrar dinero o ahorrar tiempo?"
            ])
            guidance["context_actions"].append("gather_basic_preferences")
        
        return guidance
    
    def _calculate_personalization_level(self, context: Dict[str, Any]) -> str:
        """Calcula nivel de personalización disponible"""
        overall_confidence = self._calculate_overall_confidence(context["anchors"])
        
        if overall_confidence > 0.7:
            return "high"
        elif overall_confidence > 0.4:
            return "medium"
        else:
            return "low"
    
    async def get_user_context_summary(self, user_id: str) -> Dict[str, Any]:
        """Obtiene resumen del contexto del usuario para el GPT"""
        try:
            user_profile = await self._load_or_create_user_profile(user_id)
            context_summary = self._generate_context_summary(user_profile)
            
            return {
                "user_id": user_id,
                "context_summary": context_summary,
                "last_updated": datetime.now().isoformat(),
                "profile_exists": len(user_profile.get("recent_interactions", [])) > 0
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo contexto para usuario {user_id}: {str(e)}")
            return {
                "user_id": user_id,
                "context_summary": None,
                "error": str(e),
                "profile_exists": False
            }
    
    async def cleanup_expired_data(self):
        """Limpia datos expirados según políticas de retención"""
        async with self.SessionLocal() as session:
            try:
                # Limpiar usuarios temporales expirados
                cleanup_users_query = text("""
                    DELETE FROM usuarios 
                    WHERE is_temporary = true AND expires_at < :current_time
                """)
                
                # Limpiar cache expirado
                cleanup_cache_query = text("""
                    DELETE FROM anonymous_cache 
                    WHERE expires_at < :current_time
                """)
                
                current_time = datetime.now()
                
                await session.execute(cleanup_users_query, {"current_time": current_time})
                await session.execute(cleanup_cache_query, {"current_time": current_time})
                
                await session.commit()
                
                logger.info("Limpieza de datos expirados completada")
                
            except Exception as e:
                logger.error(f"Error en limpieza de datos: {str(e)}")
                await session.rollback()


# Función de utilidad para crear instancia del servicio
def create_conversation_service(database_url: str = None) -> ConversationService:
    """
    Crea una instancia del ConversationService
    
    Args:
        database_url: URL de conexión a la base de datos
    
    Returns:
        Instancia configurada del ConversationService
    """
    return ConversationService(database_url=database_url)


# Ejemplo de uso
if __name__ == "__main__":
    import asyncio
    
    async def example_usage():
        """Ejemplo de uso del ConversationService"""
        
        # Crear servicio
        service = create_conversation_service("sqlite:///test_conversation.db")
        
        # Simular interacción de usuario
        interaction_data = {
            "productos": ["leche soprole", "pan ideal", "arroz"],
            "ubicacion": [-33.4489, -70.6693],  # Las Condes, Santiago
            "decision_tomada": "equilibrio",
            "supermercados_visitados": ["jumbo", "lider"],
            "satisfaccion": 4.2,
            "context_data": {
                "session_type": "regular_shopping",
                "time_of_day": "morning"
            }
        }
        
        # Procesar interacción
        result = await service.process_user_interaction("test_user_123", interaction_data)
        
        print("Resultado del procesamiento:")
        print(json.dumps(result, indent=2, default=str))
        
        # Obtener resumen de contexto
        context_summary = await service.get_user_context_summary("test_user_123")
        
        print("\nResumen de contexto:")
        print(json.dumps(context_summary, indent=2, default=str))
    
    # Ejecutar ejemplo
    asyncio.run(example_usage())

