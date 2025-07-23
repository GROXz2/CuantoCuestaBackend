"""
Modelo de categorías de productos
"""
from sqlalchemy import Column, String, Text, Boolean, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.core.database import Base



class Category(Base):
    """Modelo de categoría de productos"""
    
    __tablename__ = "categories"
    __table_args__ = {"schema": "products"}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True, index=True)
    slug = Column(String(100), nullable=False, unique=True, index=True)
    description = Column(Text)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("products.categories.id"))
    icon_url = Column(String(255))
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relaciones
    parent = relationship("Category", remote_side=[id], backref="children")
    products = relationship("Product", back_populates="category")
    
    def __repr__(self):
        return f"<Category(id={self.id}, name='{self.name}')>"
    
    @property
    def full_name(self):
        """Nombre completo incluyendo categoría padre"""
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name

