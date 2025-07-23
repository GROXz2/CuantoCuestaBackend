"""
Modelo de precios
"""
from sqlalchemy import Column, String, DECIMAL, DateTime, Integer, ForeignKey, UniqueConstraint, func, Boolean, Text, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base


class Price(Base):
    """Modelo de precios de productos por tienda"""
    
    __tablename__ = "prices"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.products.id"), nullable=False, index=True)
    store_id = Column(UUID(as_uuid=True), ForeignKey("stores.stores.id"), nullable=False, index=True)
    
    # Precios
    normal_price = Column(DECIMAL(10, 2), nullable=False)
    discount_price = Column(DECIMAL(10, 2))
    discount_percentage = Column(DECIMAL(5, 2))
    
    # Stock y disponibilidad
    stock_status = Column(String(20), default="available")  # available, low_stock, out_of_stock
    
    # Promoción
    promotion_description = Column(Text)
    promotion_valid_until = Column(Date)
    
    # Metadatos
    scraped_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relaciones
    product = relationship("Product", back_populates="prices")
    store = relationship("Store", back_populates="prices")
    
    def __repr__(self):
        return f"<Price(product_id={self.product_id}, store_id={self.store_id}, price={self.normal_price})>"

