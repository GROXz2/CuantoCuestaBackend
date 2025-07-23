"""
Modelos de listas de compra
"""
from sqlalchemy import Column, String, Text, Boolean, ForeignKey, DateTime, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class ShoppingList(Base):
    """Modelo de lista de compra"""
    
    __tablename__ = "shopping_lists"
    __table_args__ = {"schema": "users"}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.users.id"), nullable=False, index=True)
    name = Column(String(150), nullable=False)
    description = Column(Text)
    
    # Configuración de optimización
    optimization_priority = Column(String(20), default="balanced")  # price, distance, balanced
    max_stores = Column(Integer, default=3)
    max_distance_km = Column(Integer, default=10)
    
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relaciones
    user = relationship("User", back_populates="shopping_lists")
    items = relationship("ShoppingListItem", back_populates="shopping_list", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ShoppingList(id={self.id}, name='{self.name}', user_id={self.user_id})>"
    
    @property
    def total_items(self):
        """Total de items en la lista"""
        return len(self.items)
    
    @property
    def purchased_items(self):
        """Items ya comprados"""
        return [item for item in self.items if item.is_purchased]
    
    @property
    def pending_items(self):
        """Items pendientes por comprar"""
        return [item for item in self.items if not item.is_purchased]
    
    @property
    def completion_percentage(self):
        """Porcentaje de completitud de la lista"""
        if not self.items:
            return 0
        return (len(self.purchased_items) / len(self.items)) * 100
    
    def is_price_priority(self):
        """Verificar si prioriza precio"""
        return self.optimization_priority == "price"
    
    def is_distance_priority(self):
        """Verificar si prioriza distancia"""
        return self.optimization_priority == "distance"
    
    def is_balanced_priority(self):
        """Verificar si usa prioridad balanceada"""
        return self.optimization_priority == "balanced"


class ShoppingListItem(Base):
    """Modelo de item de lista de compra"""
    
    __tablename__ = "shopping_list_items"
    __table_args__ = (
        UniqueConstraint('shopping_list_id', 'product_id', name='unique_list_product'),
        {"schema": "users"}
    )
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shopping_list_id = Column(UUID(as_uuid=True), ForeignKey("users.shopping_lists.id"), nullable=False, index=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.products.id"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False, default=1)
    notes = Column(Text)
    is_purchased = Column(Boolean, default=False, index=True)
    purchased_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relaciones
    shopping_list = relationship("ShoppingList", back_populates="items")
    product = relationship("Product", back_populates="shopping_list_items")
    
    def __repr__(self):
        return f"<ShoppingListItem(id={self.id}, product_id={self.product_id}, quantity={self.quantity})>"
    
    def mark_as_purchased(self):
        """Marcar item como comprado"""
        self.is_purchased = True
        self.purchased_at = func.now()
    
    def mark_as_pending(self):
        """Marcar item como pendiente"""
        self.is_purchased = False
        self.purchased_at = None

