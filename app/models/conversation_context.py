"""
Modelos de datos para el contexto conversacional
===============================================

Modelos SQLAlchemy para gestionar el contexto conversacional y superar
las limitaciones de memoria de ChatGPT.
"""

from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer, Float, JSON, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime, timedelta
import uuid

from app.core.database import Base


class Usuario(Base):
    """
    Modelo para usuarios del sistema conversacional
    
    Gestiona tanto usuarios temporales (sesiones) como persistentes,
    con políticas de expiración y privacidad.
    """
    __tablename__ = "usuarios"
    
    # Campos principales
    user_id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
        comment="ID único del usuario"
    )
    
    session_id = Column(
        String(255), 
        unique=True, 
        nullable=True,
        comment="ID de sesión para usuarios temporales"
    )
    
    created_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(),
        comment="Fecha de creación"
    )
    
    expires_at = Column(
        DateTime(timezone=True), 
        nullable=True,
        comment="Fecha de expiración (NULL para usuarios persistentes)"
    )
    
    is_temporary = Column(
        Boolean, 
        default=True,
        comment="Si el usuario es temporal o persistente"
    )
    
    last_activity = Column(
        DateTime(timezone=True), 
        server_default=func.now(),
        onupdate=func.now(),
        comment="Última actividad del usuario"
    )
    
    privacy_consent = Column(
        JSONB, 
        nullable=True,
        comment="Configuración de privacidad y consentimientos"
    )
    
    # Relaciones
    contexts = relationship("UserContext", back_populates="user", cascade="all, delete-orphan")
    interactions = relationship("UserInteraction", back_populates="user", cascade="all, delete-orphan")
    anchors = relationship("ContextualAnchor", back_populates="user", cascade="all, delete-orphan")
    changes = relationship("ContextChange", back_populates="user", cascade="all, delete-orphan")
    
    # Índices
    __table_args__ = (
        Index('idx_session_id', 'session_id'),
        Index('idx_expires_at', 'expires_at'),
        Index('idx_last_activity', 'last_activity'),
    )
    
    def __repr__(self):
        return f"<Usuario(user_id={self.user_id}, session_id={self.session_id}, temporary={self.is_temporary})>"
    
    @property
    def is_expired(self):
        """Verificar si el usuario ha expirado"""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at
    
    def extend_expiration(self, days: int = 7):
        """Extender la fecha de expiración"""
        if self.is_temporary:
            self.expires_at = datetime.utcnow() + timedelta(days=days)


class UserContext(Base):
    """
    Modelo para contextos de usuario
    
    Almacena diferentes contextos (hogar, trabajo, viaje) con datos
    geográficos y preferencias específicas.
    """
    __tablename__ = "user_context"
    
    # Campos principales
    context_id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
        comment="ID único del contexto"
    )
    
    user_id = Column(
        UUID(as_uuid=True), 
        ForeignKey('usuarios.user_id', ondelete='CASCADE'),
        nullable=False,
        comment="ID del usuario propietario"
    )
    
    context_type = Column(
        String(50), 
        nullable=False,
        comment="Tipo de contexto (home, work, travel, etc.)"
    )
    
    # Datos geográficos
    ubicacion_lat = Column(
        Float(precision=8), 
        nullable=True,
        comment="Latitud exacta"
    )
    
    ubicacion_lng = Column(
        Float(precision=8), 
        nullable=True,
        comment="Longitud exacta"
    )
    
    ubicacion_hash = Column(
        String(64), 
        nullable=True,
        comment="Hash de ubicación para búsquedas anónimas"
    )
    
    # Datos de contexto
    preferencias = Column(
        JSONB, 
        nullable=True,
        comment="Preferencias específicas del contexto"
    )
    
    # Metadatos
    created_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(),
        comment="Fecha de creación"
    )
    
    updated_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(),
        onupdate=func.now(),
        comment="Fecha de última actualización"
    )
    
    is_active = Column(
        Boolean, 
        default=True,
        comment="Si el contexto está activo"
    )
    
    # Relaciones
    user = relationship("Usuario", back_populates="contexts")
    interactions = relationship("UserInteraction", back_populates="context")
    
    # Índices
    __table_args__ = (
        Index('idx_user_context', 'user_id', 'context_type'),
        Index('idx_ubicacion_hash', 'ubicacion_hash'),
        Index('idx_context_active', 'is_active'),
    )
    
    def __repr__(self):
        return f"<UserContext(context_id={self.context_id}, type={self.context_type}, active={self.is_active})>"


class UserInteraction(Base):
    """
    Modelo para interacciones de usuario
    
    Almacena el historial de interacciones para análisis de patrones
    y detección de cambios de contexto.
    """
    __tablename__ = "user_interactions"
    
    # Campos principales
    interaction_id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
        comment="ID único de la interacción"
    )
    
    user_id = Column(
        UUID(as_uuid=True), 
        ForeignKey('usuarios.user_id', ondelete='CASCADE'),
        nullable=False,
        comment="ID del usuario"
    )
    
    context_id = Column(
        UUID(as_uuid=True), 
        ForeignKey('user_context.context_id'),
        nullable=True,
        comment="ID del contexto asociado"
    )
    
    # Datos de la interacción
    interaction_data = Column(
        JSONB, 
        nullable=False,
        comment="Datos completos de la interacción"
    )
    
    timestamp = Column(
        DateTime(timezone=True), 
        server_default=func.now(),
        comment="Timestamp de la interacción"
    )
    
    interaction_hash = Column(
        String(64), 
        nullable=True,
        comment="Hash para cache anónimo"
    )
    
    # Campos derivados para análisis rápido
    intent = Column(
        String(100), 
        nullable=True,
        comment="Intención detectada"
    )
    
    satisfaction_score = Column(
        Float, 
        nullable=True,
        comment="Score de satisfacción (1-5)"
    )
    
    products_count = Column(
        Integer, 
        default=0,
        comment="Número de productos mencionados"
    )
    
    # Relaciones
    user = relationship("Usuario", back_populates="interactions")
    context = relationship("UserContext", back_populates="interactions")
    
    # Índices
    __table_args__ = (
        Index('idx_user_timestamp', 'user_id', 'timestamp'),
        Index('idx_interaction_hash', 'interaction_hash'),
        Index('idx_intent', 'intent'),
        Index('idx_satisfaction', 'satisfaction_score'),
    )
    
    def __repr__(self):
        return f"<UserInteraction(interaction_id={self.interaction_id}, intent={self.intent})>"


class AnonymousCache(Base):
    """
    Modelo para cache anónimo compartible
    
    Almacena resultados de optimización anonimizados que pueden
    reutilizarse sin comprometer la privacidad.
    """
    __tablename__ = "anonymous_cache"
    
    # Campos principales
    cache_id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
        comment="ID único del cache"
    )
    
    query_hash = Column(
        String(64), 
        unique=True, 
        nullable=False,
        comment="Hash único de la consulta"
    )
    
    region_code = Column(
        String(10), 
        nullable=False,
        comment="Código de región geográfica"
    )
    
    # Datos de la consulta y resultado
    product_categories = Column(
        JSONB, 
        nullable=False,
        comment="Categorías de productos consultados"
    )
    
    optimization_params = Column(
        JSONB, 
        nullable=False,
        comment="Parámetros de optimización"
    )
    
    result_data = Column(
        JSONB, 
        nullable=False,
        comment="Resultado de la optimización"
    )
    
    # Metadatos de uso
    usage_count = Column(
        Integer, 
        default=1,
        comment="Número de veces utilizado"
    )
    
    created_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(),
        comment="Fecha de creación"
    )
    
    expires_at = Column(
        DateTime(timezone=True), 
        nullable=True,
        comment="Fecha de expiración"
    )
    
    # Índices
    __table_args__ = (
        Index('idx_query_hash', 'query_hash'),
        Index('idx_region_code', 'region_code'),
        Index('idx_expires_at', 'expires_at'),
        Index('idx_usage_count', 'usage_count'),
    )
    
    def __repr__(self):
        return f"<AnonymousCache(cache_id={self.cache_id}, region={self.region_code}, usage={self.usage_count})>"
    
    @property
    def is_expired(self):
        """Verificar si el cache ha expirado"""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at
    
    def increment_usage(self):
        """Incrementar contador de uso"""
        self.usage_count += 1


class ContextChange(Base):
    """
    Modelo para cambios de contexto detectados
    
    Registra eventos de drift contextual para análisis y mejora
    del sistema de detección.
    """
    __tablename__ = "context_changes"
    
    # Campos principales
    change_id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
        comment="ID único del cambio"
    )
    
    user_id = Column(
        UUID(as_uuid=True), 
        ForeignKey('usuarios.user_id', ondelete='CASCADE'),
        nullable=False,
        comment="ID del usuario"
    )
    
    # Datos del cambio
    change_type = Column(
        String(50), 
        nullable=False,
        comment="Tipo de cambio detectado"
    )
    
    detection_algorithm = Column(
        String(50), 
        nullable=False,
        comment="Algoritmo que detectó el cambio"
    )
    
    change_magnitude = Column(
        Float, 
        nullable=False,
        comment="Magnitud del cambio (0-1)"
    )
    
    confidence_score = Column(
        Float, 
        nullable=False,
        comment="Confianza en la detección (0-1)"
    )
    
    affected_anchors = Column(
        JSONB, 
        nullable=True,
        comment="Anclas contextuales afectadas"
    )
    
    detection_details = Column(
        JSONB, 
        nullable=True,
        comment="Detalles técnicos de la detección"
    )
    
    # Metadatos
    detection_timestamp = Column(
        DateTime(timezone=True), 
        server_default=func.now(),
        comment="Timestamp de la detección"
    )
    
    was_confirmed = Column(
        Boolean, 
        nullable=True,
        comment="Si el usuario confirmó el cambio"
    )
    
    resolution_action = Column(
        String(100), 
        nullable=True,
        comment="Acción tomada para resolver el cambio"
    )
    
    # Relaciones
    user = relationship("Usuario", back_populates="changes")
    
    # Índices
    __table_args__ = (
        Index('idx_user_detection', 'user_id', 'detection_timestamp'),
        Index('idx_change_type', 'change_type'),
        Index('idx_algorithm', 'detection_algorithm'),
        Index('idx_confidence', 'confidence_score'),
    )
    
    def __repr__(self):
        return f"<ContextChange(change_id={self.change_id}, type={self.change_type}, confidence={self.confidence_score})>"


# Funciones auxiliares para el modelo

def create_temporary_user(session_id: str, expiration_days: int = 7) -> Usuario:
    """
    Crear un usuario temporal con expiración automática
    
    Args:
        session_id: ID de sesión único
        expiration_days: Días hasta la expiración
        
    Returns:
        Usuario: Instancia del usuario temporal
    """
    expiration_date = datetime.utcnow() + timedelta(days=expiration_days)
    
    return Usuario(
        session_id=session_id,
        is_temporary=True,
        expires_at=expiration_date,
        privacy_consent={
            "data_collection": True,
            "analytics": True,
            "personalization": True,
            "retention_days": expiration_days
        }
    )


def create_persistent_user(user_id: str = None) -> Usuario:
    """
    Crear un usuario persistente
    
    Args:
        user_id: ID específico del usuario (opcional)
        
    Returns:
        Usuario: Instancia del usuario persistente
    """
    user = Usuario(
        is_temporary=False,
        expires_at=None,
        privacy_consent={
            "data_collection": True,
            "analytics": True,
            "personalization": True,
            "retention_indefinite": True
        }
    )
    
    if user_id:
        user.user_id = uuid.UUID(user_id)
    
    return user


# Exportar modelos
__all__ = [
    "Usuario",
    "UserContext", 
    "UserInteraction",
    "AnonymousCache",
    "ContextChange",
    "create_temporary_user",
    "create_persistent_user"
]

