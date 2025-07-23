"""
Modelo de usuarios
"""
from sqlalchemy import Column, String, Boolean, DateTime, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from geoalchemy2 import Geography
import uuid

from app.core.database import Base


class User(Base):
    """Modelo de usuario"""
    
    __tablename__ = "users"
    __table_args__ = {"schema": "users"}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    phone = Column(String(20))
    
    # Preferencias del usuario
    preferred_commune = Column(String(100))
    preferred_location = Column(Geography(geometry_type='POINT', srid=4326))
    max_distance_km = Column(Integer, default=10)
    price_priority = Column(Integer, default=70)  # 0-100, vs distance priority
    
    # Configuración de notificaciones
    email_notifications = Column(Boolean, default=True)
    price_alert_notifications = Column(Boolean, default=True)
    
    # Estado del usuario
    is_active = Column(Boolean, default=True, index=True)
    email_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_login = Column(DateTime(timezone=True))
    
    # Relaciones
    shopping_lists = relationship("ShoppingList", back_populates="user")
    
    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}')>"
    
    @property
    def full_name(self):
        """Nombre completo del usuario"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        return self.email.split('@')[0]
    
    @property
    def coordinates(self):
        """Obtener coordenadas preferidas como tupla (lat, lon)"""
        if self.preferred_location:
            # PostGIS devuelve en formato WKT: POINT(lon lat)
            coords = str(self.preferred_location).replace('POINT(', '').replace(')', '').split()
            return float(coords[1]), float(coords[0])  # lat, lon
        return None, None
    
    @property
    def distance_priority(self):
        """Prioridad de distancia (complemento de price_priority)"""
        return 100 - self.price_priority
    
    def prefers_price_over_distance(self):
        """Verificar si prefiere precio sobre distancia"""
        return self.price_priority > 50

