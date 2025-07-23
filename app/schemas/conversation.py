"""
Schemas para el Conversation Service
===================================

Schemas de Pydantic para validación de requests y responses del sistema
de gestión de contexto conversacional.
"""

from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from pydantic import BaseModel, Field, validator
import time


# Schemas de Request

class ConversationRequest(BaseModel):
    """
    Schema para requests de procesamiento de conversación
    """
    user_id: str = Field(
        ..., 
        description="Identificador único del usuario (session_id o user_id persistente)",
        min_length=1,
        max_length=255
    )
    
    interaction_data: Dict[str, Any] = Field(
        ...,
        description="Datos de la interacción del usuario"
    )
    
    session_metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Metadatos de la sesión (ubicación, dispositivo, etc.)"
    )
    
    @validator('interaction_data')
    def validate_interaction_data(cls, v):
        """Validar que interaction_data tenga campos requeridos"""
        required_fields = ['message', 'timestamp']
        for field in required_fields:
            if field not in v:
                raise ValueError(f"Campo requerido '{field}' faltante en interaction_data")
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "user_id": "temp_user_abc123",
                "interaction_data": {
                    "message": "¿Cuánto cuesta el pan?",
                    "timestamp": 1640995200.0,
                    "products_mentioned": ["pan"],
                    "intent": "price_inquiry"
                },
                "session_metadata": {
                    "location": {"lat": -33.4489, "lng": -70.6693},
                    "device": "mobile",
                    "platform": "gpt"
                }
            }
        }


class UserProfileRequest(BaseModel):
    """
    Schema para requests de creación/actualización de perfil
    """
    user_id: str = Field(
        ...,
        description="Identificador único del usuario",
        min_length=1,
        max_length=255
    )
    
    profile_data: Dict[str, Any] = Field(
        ...,
        description="Datos del perfil del usuario"
    )
    
    is_temporary: bool = Field(
        default=True,
        description="Si el perfil es temporal (expira) o persistente"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "user_id": "temp_user_abc123",
                "profile_data": {
                    "preferences": {
                        "optimization_priority": "savings",
                        "max_stores": 2,
                        "preferred_brands": ["soprole", "ideal"]
                    },
                    "demographics": {
                        "has_children": True,
                        "allergies": ["lactose"]
                    },
                    "locations": {
                        "home": {"lat": -33.4489, "lng": -70.6693},
                        "work": {"lat": -33.4200, "lng": -70.6100}
                    }
                },
                "is_temporary": True
            }
        }


# Schemas de Response

class ContextSummary(BaseModel):
    """
    Schema para resumen de contexto del usuario
    """
    profile_strength: float = Field(
        ...,
        description="Fortaleza del perfil (0-1)",
        ge=0.0,
        le=1.0
    )
    
    active_anchors: Dict[str, Any] = Field(
        ...,
        description="Anclas contextuales activas"
    )
    
    recent_patterns: Dict[str, Any] = Field(
        ...,
        description="Patrones recientes detectados"
    )
    
    confidence_metrics: Dict[str, float] = Field(
        ...,
        description="Métricas de confianza por dimensión"
    )


class DriftInfo(BaseModel):
    """
    Schema para información de drift detectado
    """
    drift_detected: bool = Field(
        ...,
        description="Si se detectó drift contextual"
    )
    
    drift_type: Optional[str] = Field(
        None,
        description="Tipo de drift detectado"
    )
    
    confidence_score: float = Field(
        ...,
        description="Confianza en la detección (0-1)",
        ge=0.0,
        le=1.0
    )
    
    affected_dimensions: List[str] = Field(
        default_factory=list,
        description="Dimensiones afectadas por el drift"
    )


class ConversationGuidance(BaseModel):
    """
    Schema para guía conversacional
    """
    suggested_questions: List[str] = Field(
        default_factory=list,
        description="Preguntas sugeridas para el usuario"
    )
    
    context_clarifications: List[str] = Field(
        default_factory=list,
        description="Clarificaciones de contexto necesarias"
    )
    
    personalization_tips: List[str] = Field(
        default_factory=list,
        description="Tips para mejorar personalización"
    )


class ConversationResponse(BaseModel):
    """
    Schema para responses de procesamiento de conversación
    """
    success: bool = Field(
        ...,
        description="Si el procesamiento fue exitoso"
    )
    
    context_summary: ContextSummary = Field(
        ...,
        description="Resumen del contexto actualizado"
    )
    
    recommendations: Dict[str, Any] = Field(
        ...,
        description="Recomendaciones basadas en el contexto"
    )
    
    drift_info: DriftInfo = Field(
        ...,
        description="Información sobre drift detectado"
    )
    
    conversation_guidance: ConversationGuidance = Field(
        default_factory=ConversationGuidance,
        description="Guía para la conversación"
    )
    
    processing_time_ms: float = Field(
        ...,
        description="Tiempo de procesamiento en milisegundos"
    )
    
    timestamp: float = Field(
        default_factory=time.time,
        description="Timestamp de la respuesta"
    )


class ContextSummaryResponse(BaseModel):
    """
    Schema para responses de resumen de contexto
    """
    success: bool = Field(
        ...,
        description="Si la operación fue exitosa"
    )
    
    user_id: str = Field(
        ...,
        description="ID del usuario"
    )
    
    context_summary: Dict[str, Any] = Field(
        ...,
        description="Resumen completo del contexto"
    )
    
    timestamp: float = Field(
        default_factory=time.time,
        description="Timestamp de la respuesta"
    )


class UserProfileResponse(BaseModel):
    """
    Schema para responses de perfil de usuario
    """
    success: bool = Field(
        ...,
        description="Si la operación fue exitosa"
    )
    
    user_id: str = Field(
        ...,
        description="ID del usuario"
    )
    
    profile_data: Dict[str, Any] = Field(
        ...,
        description="Datos del perfil actualizado"
    )
    
    profile_strength: float = Field(
        ...,
        description="Fortaleza del perfil (0-1)",
        ge=0.0,
        le=1.0
    )
    
    created_at: datetime = Field(
        ...,
        description="Fecha de creación del perfil"
    )
    
    updated_at: datetime = Field(
        ...,
        description="Fecha de última actualización"
    )
    
    timestamp: float = Field(
        default_factory=time.time,
        description="Timestamp de la respuesta"
    )


class DriftDetectionResponse(BaseModel):
    """
    Schema para responses de detección de drift
    """
    success: bool = Field(
        ...,
        description="Si el análisis fue exitoso"
    )
    
    user_id: str = Field(
        ...,
        description="ID del usuario analizado"
    )
    
    drift_detected: bool = Field(
        ...,
        description="Si se detectó drift"
    )
    
    drift_type: Optional[str] = Field(
        None,
        description="Tipo de drift detectado"
    )
    
    confidence_score: float = Field(
        ...,
        description="Confianza en la detección (0-1)",
        ge=0.0,
        le=1.0
    )
    
    affected_anchors: List[str] = Field(
        default_factory=list,
        description="Anclas contextuales afectadas"
    )
    
    detection_details: Dict[str, Any] = Field(
        ...,
        description="Detalles técnicos de la detección"
    )
    
    recommended_actions: List[str] = Field(
        default_factory=list,
        description="Acciones recomendadas"
    )
    
    analysis_period_days: int = Field(
        ...,
        description="Período de análisis en días"
    )
    
    timestamp: float = Field(
        default_factory=time.time,
        description="Timestamp del análisis"
    )


# Schemas para modelos internos

class ContextualAnchorData(BaseModel):
    """
    Schema para datos de ancla contextual
    """
    name: str = Field(
        ...,
        description="Nombre de la ancla"
    )
    
    weight: float = Field(
        ...,
        description="Peso de la ancla (0-1)",
        ge=0.0,
        le=1.0
    )
    
    current_value: Any = Field(
        ...,
        description="Valor actual de la ancla"
    )
    
    confidence: float = Field(
        ...,
        description="Confianza en el valor (0-1)",
        ge=0.0,
        le=1.0
    )
    
    stability_threshold: float = Field(
        ...,
        description="Umbral de estabilidad"
    )
    
    decay_rate: float = Field(
        ...,
        description="Tasa de decaimiento temporal"
    )
    
    last_updated: datetime = Field(
        ...,
        description="Última actualización"
    )


class InteractionData(BaseModel):
    """
    Schema para datos de interacción
    """
    interaction_id: str = Field(
        ...,
        description="ID único de la interacción"
    )
    
    user_id: str = Field(
        ...,
        description="ID del usuario"
    )
    
    message: str = Field(
        ...,
        description="Mensaje del usuario"
    )
    
    intent: Optional[str] = Field(
        None,
        description="Intención detectada"
    )
    
    products_mentioned: List[str] = Field(
        default_factory=list,
        description="Productos mencionados"
    )
    
    location: Optional[Dict[str, float]] = Field(
        None,
        description="Ubicación del usuario"
    )
    
    satisfaction_score: Optional[float] = Field(
        None,
        description="Score de satisfacción (1-5)",
        ge=1.0,
        le=5.0
    )
    
    timestamp: datetime = Field(
        ...,
        description="Timestamp de la interacción"
    )


# Schemas de configuración

class ConversationConfig(BaseModel):
    """
    Schema para configuración del conversation service
    """
    max_context_window: int = Field(
        default=50,
        description="Tamaño máximo de ventana de contexto"
    )
    
    drift_detection_sensitivity: float = Field(
        default=0.7,
        description="Sensibilidad de detección de drift (0-1)",
        ge=0.0,
        le=1.0
    )
    
    anchor_weights: Dict[str, float] = Field(
        default_factory=dict,
        description="Pesos por defecto de las anclas"
    )
    
    temporal_decay_factor: float = Field(
        default=0.95,
        description="Factor de decaimiento temporal diario"
    )
    
    anonymization_delay_hours: int = Field(
        default=24,
        description="Horas antes de anonimizar datos"
    )


# Exportar todos los schemas
__all__ = [
    "ConversationRequest",
    "UserProfileRequest", 
    "ConversationResponse",
    "ContextSummaryResponse",
    "UserProfileResponse",
    "DriftDetectionResponse",
    "ContextSummary",
    "DriftInfo",
    "ConversationGuidance",
    "ContextualAnchorData",
    "InteractionData",
    "ConversationConfig"
]

