"""
Modelo de tiendas
"""
from sqlalchemy import Column, String, Text, Boolean, ForeignKey, DateTime, Computed
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from geoalchemy2 import Geography
from shapely.geometry import Point
from geoalchemy2.shape import from_shape
import uuid

from app.core.database import Base


class Store(Base):
    """Modelo de tienda física"""
    
    __tablename__ = "stores"
    __table_args__ = {"schema": "stores"}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    supermarket_id = Column(UUID(as_uuid=True), ForeignKey("stores.supermarkets.id"), nullable=False)
    name = Column(String(150), nullable=False, index=True)
    address = Column(Text, nullable=False)
    commune = Column(String(100), nullable=False, index=True)
    region = Column(String(100), nullable=False)
    phone = Column(String(20))
    email = Column(String(100))
    
    # Campos normalizados para búsqueda de caracteres especiales
    commune_normalized = Column(
    String(100),
    index=True
)
    commune_slug = Column(
    String(100),
    index=True
)
    
    # Geolocalización
    location = Column(Geography(geometry_type='POINT', srid=4326))
    
    # Horarios (JSON flexible)
    opening_hours = Column(JSONB)
    
    # Servicios disponibles
    has_pharmacy = Column(Boolean, default=False)
    has_bakery = Column(Boolean, default=False)
    has_parking = Column(Boolean, default=False)
    services = Column(JSONB)  # Lista de servicios adicionales
    
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relaciones
    supermarket = relationship("Supermarket", back_populates="stores")
    prices = relationship("Price", back_populates="store")
    
    def __repr__(self):
        return f"<Store(id={self.id}, name='{self.name}', commune='{self.commune}')>"
    
    @property
    def full_name(self):
        """Nombre completo de la tienda"""
        return f"{self.supermarket.name} {self.commune}" if self.supermarket else self.name
    
    @property
    def coordinates(self):
        """Obtener coordenadas como tupla (lat, lon)"""
        if self.location:
            # PostGIS devuelve en formato WKT: POINT(lon lat)
            coords = str(self.location).replace('POINT(', '').replace(')', '').split()
            return float(coords[1]), float(coords[0])  # lat, lon
        return None, None
    
    def coordinates(self, value):
        """Permite asignar coordenadas como tupla (lat, lon)"""
        lat, lon = value
        self.location = from_shape(Point(lon, lat), srid=4326)

    def is_open_now(self):
        """Verificar si la tienda está abierta ahora"""
        # TODO: Implementar lógica de horarios
        # Por ahora retorna True
        return True
    
    def get_services_list(self):
        """Obtener lista de servicios disponibles"""
        services = []
        if self.has_pharmacy:
            services.append("farmacia")
        if self.has_bakery:
            services.append("panaderia")
        if self.has_parking:
            services.append("estacionamiento")
        
        if self.services and isinstance(self.services, list):
            services.extend(self.services)
        
        return list(set(services))  # Eliminar duplicados

