"""
Modelos de datos para anclas contextuales
=========================================

Modelos SQLAlchemy para el sistema de Weighted Moving Average con
Contextual Anchors que resuelve el problema de drift contextual.
"""

from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer, Float, JSON, ForeignKey, Index, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func
from datetime import datetime, timedelta
import uuid
import json

from app.core.database import Base


class ContextualAnchor(Base):
    """
    Modelo para anclas contextuales del sistema WMA
    
    Las anclas contextuales son puntos de referencia estables que definen
    el perfil del usuario y permiten detectar cambios significativos.
    """
    __tablename__ = "contextual_anchors"
    
    # Campos principales
    anchor_id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
        comment="ID único del ancla"
    )
    
    user_id = Column(
        UUID(as_uuid=True), 
        ForeignKey('usuarios.user_id', ondelete='CASCADE'),
        nullable=False,
        comment="ID del usuario propietario"
    )
    
    anchor_name = Column(
        String(100), 
        nullable=False,
        comment="Nombre del ancla (ubicacion_hogar, preferencias_precio, etc.)"
    )
    
    # Datos del ancla
    anchor_value = Column(
        JSONB, 
        nullable=False,
        comment="Valor actual del ancla"
    )
    
    # Métricas de confianza y estabilidad
    confidence_score = Column(
        Float, 
        nullable=False,
        default=0.0,
        comment="Score de confianza (0.00 a 1.00)"
    )
    
    stability_threshold = Column(
        Float, 
        nullable=False,
        default=0.7,
        comment="Umbral de estabilidad para detectar cambios"
    )
    
    # Configuración del ancla
    weight = Column(
        Float, 
        nullable=False,
        default=1.0,
        comment="Peso del ancla en el sistema WMA"
    )
    
    decay_rate = Column(
        Float, 
        nullable=False,
        default=0.95,
        comment="Tasa de decaimiento temporal diario"
    )
    
    learning_rate = Column(
        Float, 
        nullable=False,
        default=0.1,
        comment="Tasa de aprendizaje para actualizaciones"
    )
    
    # Metadatos temporales
    created_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(),
        comment="Fecha de creación"
    )
    
    last_updated = Column(
        DateTime(timezone=True), 
        server_default=func.now(),
        onupdate=func.now(),
        comment="Última actualización"
    )
    
    update_count = Column(
        Integer, 
        default=1,
        comment="Número de actualizaciones"
    )
    
    # Estado del ancla
    is_active = Column(
        Boolean, 
        default=True,
        comment="Si el ancla está activa"
    )
    
    is_stable = Column(
        Boolean, 
        default=False,
        comment="Si el ancla ha alcanzado estabilidad"
    )
    
    # Datos de análisis
    historical_values = Column(
        JSONB, 
        nullable=True,
        comment="Historial de valores para análisis de drift"
    )
    
    drift_alerts = Column(
        JSONB, 
        nullable=True,
        comment="Alertas de drift detectadas"
    )
    
    # Relaciones
    user = relationship("Usuario", back_populates="anchors")
    
    # Constraints
    __table_args__ = (
        Index('idx_user_anchor', 'user_id', 'anchor_name'),
        Index('idx_confidence_score', 'confidence_score'),
        Index('idx_last_updated', 'last_updated'),
        Index('idx_active_stable', 'is_active', 'is_stable'),
        CheckConstraint('confidence_score >= 0.0 AND confidence_score <= 1.0', name='check_confidence_range'),
        CheckConstraint('stability_threshold >= 0.0 AND stability_threshold <= 1.0', name='check_stability_range'),
        CheckConstraint('weight >= 0.0', name='check_weight_positive'),
        CheckConstraint('decay_rate >= 0.0 AND decay_rate <= 1.0', name='check_decay_range'),
        CheckConstraint('learning_rate >= 0.0 AND learning_rate <= 1.0', name='check_learning_range'),
    )
    
    def __repr__(self):
        return f"<ContextualAnchor(anchor_id={self.anchor_id}, name={self.anchor_name}, confidence={self.confidence_score})>"
    
    @validates('anchor_name')
    def validate_anchor_name(self, key, anchor_name):
        """Validar que el nombre del ancla sea válido"""
        valid_names = [
            'ubicacion_hogar', 'ubicacion_trabajo', 'ubicacion_frecuente',
            'preferencias_precio', 'preferencias_marca', 'preferencias_categoria',
            'patrones_horarios', 'patrones_frecuencia', 'patrones_estacionales',
            'supermercados_preferidos', 'productos_frecuentes', 'presupuesto_promedio',
            'sensibilidad_distancia', 'tolerancia_tiempo', 'optimizacion_preferida'
        ]
        
        if anchor_name not in valid_names:
            raise ValueError(f"Nombre de ancla inválido: {anchor_name}")
        
        return anchor_name
    
    def update_value(self, new_value, confidence_boost=0.0):
        """
        Actualizar el valor del ancla usando Weighted Moving Average
        
        Args:
            new_value: Nuevo valor para el ancla
            confidence_boost: Boost adicional de confianza (0-0.2)
        """
        if not self.anchor_value:
            # Primera actualización
            self.anchor_value = new_value
            self.confidence_score = min(0.3 + confidence_boost, 1.0)
        else:
            # Weighted Moving Average
            alpha = self.learning_rate * (1.0 + confidence_boost)
            
            if isinstance(new_value, dict) and isinstance(self.anchor_value, dict):
                # Actualización de diccionarios
                updated_value = {}
                for key in set(list(new_value.keys()) + list(self.anchor_value.keys())):
                    if key in new_value and key in self.anchor_value:
                        if isinstance(new_value[key], (int, float)) and isinstance(self.anchor_value[key], (int, float)):
                            updated_value[key] = (1 - alpha) * self.anchor_value[key] + alpha * new_value[key]
                        else:
                            updated_value[key] = new_value[key]  # Usar nuevo valor para no-numéricos
                    elif key in new_value:
                        updated_value[key] = new_value[key]
                    else:
                        updated_value[key] = self.anchor_value[key]
                
                self.anchor_value = updated_value
            
            elif isinstance(new_value, (int, float)) and isinstance(self.anchor_value, (int, float)):
                # Actualización numérica simple
                self.anchor_value = (1 - alpha) * self.anchor_value + alpha * new_value
            
            else:
                # Reemplazo directo para tipos incompatibles
                self.anchor_value = new_value
            
            # Actualizar confianza
            confidence_increase = self.learning_rate * 0.1 + confidence_boost
            self.confidence_score = min(self.confidence_score + confidence_increase, 1.0)
        
        # Actualizar metadatos
        self.update_count += 1
        self.last_updated = datetime.utcnow()
        
        # Verificar estabilidad
        if self.confidence_score >= self.stability_threshold and self.update_count >= 5:
            self.is_stable = True
        
        # Guardar en historial
        self._add_to_history(new_value)
    
    def apply_temporal_decay(self, days_since_update=None):
        """
        Aplicar decaimiento temporal a la confianza del ancla
        
        Args:
            days_since_update: Días desde la última actualización (auto-calculado si None)
        """
        if days_since_update is None:
            days_since_update = (datetime.utcnow() - self.last_updated).days
        
        if days_since_update > 0:
            decay_factor = self.decay_rate ** days_since_update
            self.confidence_score *= decay_factor
            
            # Si la confianza baja mucho, marcar como inestable
            if self.confidence_score < self.stability_threshold * 0.5:
                self.is_stable = False
    
    def detect_drift(self, new_value, threshold_multiplier=1.0):
        """
        Detectar si un nuevo valor representa drift contextual
        
        Args:
            new_value: Nuevo valor a evaluar
            threshold_multiplier: Multiplicador del umbral de estabilidad
            
        Returns:
            dict: Información sobre drift detectado
        """
        if not self.anchor_value or not self.is_stable:
            return {
                "drift_detected": False,
                "reason": "anchor_not_stable",
                "confidence": 0.0
            }
        
        # Calcular diferencia según tipo de valor
        if isinstance(new_value, dict) and isinstance(self.anchor_value, dict):
            # Drift en diccionarios (ej: ubicación, preferencias)
            drift_score = self._calculate_dict_drift(new_value, self.anchor_value)
        
        elif isinstance(new_value, (int, float)) and isinstance(self.anchor_value, (int, float)):
            # Drift numérico
            if self.anchor_value != 0:
                drift_score = abs(new_value - self.anchor_value) / abs(self.anchor_value)
            else:
                drift_score = 1.0 if new_value != 0 else 0.0
        
        elif isinstance(new_value, (list, tuple)) and isinstance(self.anchor_value, (list, tuple)):
            # Drift en listas (ej: productos preferidos)
            drift_score = self._calculate_list_drift(new_value, self.anchor_value)
        
        else:
            # Drift en tipos diferentes o strings
            drift_score = 0.0 if new_value == self.anchor_value else 1.0
        
        # Determinar si hay drift
        adjusted_threshold = self.stability_threshold * threshold_multiplier
        drift_detected = drift_score > adjusted_threshold
        
        # Registrar alerta si hay drift
        if drift_detected:
            self._add_drift_alert(new_value, drift_score)
        
        return {
            "drift_detected": drift_detected,
            "drift_score": drift_score,
            "threshold_used": adjusted_threshold,
            "confidence": self.confidence_score,
            "anchor_stability": self.is_stable
        }
    
    def _calculate_dict_drift(self, new_dict, old_dict):
        """Calcular drift entre diccionarios"""
        all_keys = set(list(new_dict.keys()) + list(old_dict.keys()))
        
        if not all_keys:
            return 0.0
        
        differences = []
        for key in all_keys:
            if key in new_dict and key in old_dict:
                if isinstance(new_dict[key], (int, float)) and isinstance(old_dict[key], (int, float)):
                    if old_dict[key] != 0:
                        diff = abs(new_dict[key] - old_dict[key]) / abs(old_dict[key])
                    else:
                        diff = 1.0 if new_dict[key] != 0 else 0.0
                else:
                    diff = 0.0 if new_dict[key] == old_dict[key] else 1.0
            else:
                diff = 1.0  # Clave faltante = diferencia máxima
            
            differences.append(diff)
        
        return sum(differences) / len(differences)
    
    def _calculate_list_drift(self, new_list, old_list):
        """Calcular drift entre listas"""
        if not new_list and not old_list:
            return 0.0
        
        if not new_list or not old_list:
            return 1.0
        
        # Calcular intersección y unión
        set_new = set(new_list)
        set_old = set(old_list)
        
        intersection = len(set_new & set_old)
        union = len(set_new | set_old)
        
        if union == 0:
            return 0.0
        
        # Jaccard distance como medida de drift
        jaccard_similarity = intersection / union
        return 1.0 - jaccard_similarity
    
    def _add_to_history(self, value):
        """Agregar valor al historial"""
        if not self.historical_values:
            self.historical_values = []
        
        # Mantener solo los últimos 50 valores
        history = self.historical_values[-49:] if self.historical_values else []
        history.append({
            "value": value,
            "timestamp": datetime.utcnow().isoformat(),
            "confidence": self.confidence_score
        })
        
        self.historical_values = history
    
    def _add_drift_alert(self, new_value, drift_score):
        """Agregar alerta de drift"""
        if not self.drift_alerts:
            self.drift_alerts = []
        
        alert = {
            "timestamp": datetime.utcnow().isoformat(),
            "new_value": new_value,
            "old_value": self.anchor_value,
            "drift_score": drift_score,
            "confidence_at_detection": self.confidence_score
        }
        
        # Mantener solo las últimas 10 alertas
        alerts = self.drift_alerts[-9:] if self.drift_alerts else []
        alerts.append(alert)
        
        self.drift_alerts = alerts
    
    def get_stability_metrics(self):
        """Obtener métricas de estabilidad del ancla"""
        days_since_creation = (datetime.utcnow() - self.created_at).days
        days_since_update = (datetime.utcnow() - self.last_updated).days
        
        return {
            "anchor_name": self.anchor_name,
            "confidence_score": self.confidence_score,
            "is_stable": self.is_stable,
            "update_count": self.update_count,
            "days_since_creation": days_since_creation,
            "days_since_update": days_since_update,
            "weight": self.weight,
            "stability_threshold": self.stability_threshold,
            "recent_drift_alerts": len(self.drift_alerts) if self.drift_alerts else 0
        }


class AnchorTemplate(Base):
    """
    Modelo para plantillas de anclas contextuales
    
    Define configuraciones predeterminadas para diferentes tipos de anclas
    según el dominio de aplicación (supermercados, restaurantes, etc.).
    """
    __tablename__ = "anchor_templates"
    
    # Campos principales
    template_id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
        comment="ID único de la plantilla"
    )
    
    template_name = Column(
        String(100), 
        unique=True, 
        nullable=False,
        comment="Nombre de la plantilla"
    )
    
    domain = Column(
        String(50), 
        nullable=False,
        comment="Dominio de aplicación (supermercados, restaurantes, etc.)"
    )
    
    # Configuración de la plantilla
    default_weight = Column(
        Float, 
        nullable=False,
        default=1.0,
        comment="Peso por defecto"
    )
    
    default_stability_threshold = Column(
        Float, 
        nullable=False,
        default=0.7,
        comment="Umbral de estabilidad por defecto"
    )
    
    default_decay_rate = Column(
        Float, 
        nullable=False,
        default=0.95,
        comment="Tasa de decaimiento por defecto"
    )
    
    default_learning_rate = Column(
        Float, 
        nullable=False,
        default=0.1,
        comment="Tasa de aprendizaje por defecto"
    )
    
    # Metadatos
    description = Column(
        Text, 
        nullable=True,
        comment="Descripción de la plantilla"
    )
    
    validation_rules = Column(
        JSONB, 
        nullable=True,
        comment="Reglas de validación para valores"
    )
    
    created_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(),
        comment="Fecha de creación"
    )
    
    is_active = Column(
        Boolean, 
        default=True,
        comment="Si la plantilla está activa"
    )
    
    # Índices
    __table_args__ = (
        Index('idx_template_name', 'template_name'),
        Index('idx_domain', 'domain'),
        Index('idx_active', 'is_active'),
    )
    
    def __repr__(self):
        return f"<AnchorTemplate(template_id={self.template_id}, name={self.template_name}, domain={self.domain})>"
    
    def create_anchor_for_user(self, user_id, initial_value=None):
        """
        Crear un ancla contextual para un usuario usando esta plantilla
        
        Args:
            user_id: ID del usuario
            initial_value: Valor inicial del ancla
            
        Returns:
            ContextualAnchor: Nueva instancia de ancla
        """
        return ContextualAnchor(
            user_id=user_id,
            anchor_name=self.template_name,
            anchor_value=initial_value or {},
            weight=self.default_weight,
            stability_threshold=self.default_stability_threshold,
            decay_rate=self.default_decay_rate,
            learning_rate=self.default_learning_rate
        )


# Funciones auxiliares

def create_default_anchors_for_user(user_id: str, domain: str = "supermercados"):
    """
    Crear anclas contextuales por defecto para un nuevo usuario
    
    Args:
        user_id: ID del usuario
        domain: Dominio de aplicación
        
    Returns:
        List[ContextualAnchor]: Lista de anclas creadas
    """
    default_configs = {
        "supermercados": {
            "ubicacion_hogar": {"weight": 1.5, "threshold": 0.8},
            "preferencias_precio": {"weight": 1.2, "threshold": 0.7},
            "supermercados_preferidos": {"weight": 1.0, "threshold": 0.6},
            "productos_frecuentes": {"weight": 0.8, "threshold": 0.5},
            "patrones_horarios": {"weight": 0.6, "threshold": 0.7},
            "presupuesto_promedio": {"weight": 1.1, "threshold": 0.8}
        }
    }
    
    configs = default_configs.get(domain, default_configs["supermercados"])
    anchors = []
    
    for anchor_name, config in configs.items():
        anchor = ContextualAnchor(
            user_id=user_id,
            anchor_name=anchor_name,
            anchor_value={},
            weight=config["weight"],
            stability_threshold=config["threshold"],
            decay_rate=0.95,
            learning_rate=0.1
        )
        anchors.append(anchor)
    
    return anchors


def get_anchor_importance_weights():
    """
    Obtener pesos de importancia para diferentes tipos de anclas
    
    Returns:
        dict: Pesos por tipo de ancla
    """
    return {
        "ubicacion_hogar": 1.5,      # Muy importante para recomendaciones
        "ubicacion_trabajo": 1.2,    # Importante para contexto laboral
        "preferencias_precio": 1.3,  # Crítico para optimización
        "supermercados_preferidos": 1.1,  # Importante para filtrado
        "productos_frecuentes": 0.9, # Moderadamente importante
        "patrones_horarios": 0.7,    # Útil pero no crítico
        "presupuesto_promedio": 1.2, # Importante para recomendaciones
        "sensibilidad_distancia": 1.0,  # Importante para logística
        "tolerancia_tiempo": 0.8,    # Moderadamente importante
        "optimizacion_preferida": 1.1   # Importante para algoritmos
    }


# Exportar modelos y funciones
__all__ = [
    "ContextualAnchor",
    "AnchorTemplate",
    "create_default_anchors_for_user",
    "get_anchor_importance_weights"
]

