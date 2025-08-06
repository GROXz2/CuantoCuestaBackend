"""
Modelo de productos
"""
from sqlalchemy import Column, String, Text, Boolean, ForeignKey, DateTime, Computed, Index
from sqlalchemy.dialects.postgresql import UUID, TSVECTOR
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class Product(Base):
    """Modelo de producto"""

    __tablename__ = "products"
    __table_args__ = (
        Index("ix_products_search_vector", "search_vector", postgresql_using="gin"),
        {"schema": "products"},
    )
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, index=True)
    brand = Column(String(100), index=True)
    category_id = Column(UUID(as_uuid=True), ForeignKey("products.categories.id"), nullable=False, index=True)
    barcode = Column(String(50), unique=True, index=True)
    description = Column(Text)
    unit_type = Column(String(20), default="unidad")  # unidad, kg, litro, etc.
    unit_size = Column(String(50))  # 500g, 1L, etc.
    image_url = Column(String(255))
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Campo de búsqueda de texto completo
    search_vector = Column(
        TSVECTOR,
        Computed(
            "to_tsvector('spanish', coalesce(name, '') || ' ' || coalesce(brand, '') || ' ' || coalesce(description, ''))",
            persisted=True
        )
    )
    
    # Relaciones
    category = relationship("Category", back_populates="products")
    prices = relationship("Price", back_populates="product")
    shopping_list_items = relationship("ShoppingListItem", back_populates="product")
    
    def __repr__(self):
        return f"<Product(id={self.id}, name='{self.name}', brand='{self.brand}')>"
    
    @property
    def full_name(self):
        """Nombre completo del producto incluyendo marca"""
        if self.brand:
            return f"{self.brand} {self.name}"
        return self.name
    
    @property
    def display_unit(self):
        """Unidad de medida para mostrar"""
        if self.unit_size:
            return f"{self.unit_size}"
        return self.unit_type

