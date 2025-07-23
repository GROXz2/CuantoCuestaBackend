"""
Modelo de supermercados
"""
from sqlalchemy import Column, String, Boolean, DateTime, DECIMAL
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class Supermarket(Base):
    """Modelo de cadena de supermercados"""
    
    __tablename__ = "supermarkets"
    __table_args__ = {"schema": "stores"}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True, index=True)
    slug = Column(String(100), nullable=False, unique=True, index=True)
    logo_url = Column(String(255))
    website_url = Column(String(255))
    type = Column(String(20), default="retail", index=True)  # retail, mayorista
    minimum_purchase_amount = Column(DECIMAL(10, 2), default=0)
    delivery_available = Column(Boolean, default=False)
    pickup_available = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relaciones
    stores = relationship("Store", back_populates="supermarket")
    
    def __repr__(self):
        return f"<Supermarket(id={self.id}, name='{self.name}', type='{self.type}')>"
    
    @property
    def is_mayorista(self):
        """Verificar si es mayorista"""
        return self.type == "mayorista"
    
    @property
    def has_minimum_purchase(self):
        """Verificar si tiene compra mínima"""
        return self.minimum_purchase_amount > 0

