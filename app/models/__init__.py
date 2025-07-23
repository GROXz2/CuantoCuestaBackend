"""
Modelos de la aplicación Cuanto Cuesta
Incluye modelos del Conversation Service para gestión de contexto conversacional
"""
from .category import Category
from .product import Product
from .supermarket import Supermarket
from .store import Store
from .price import Price
from .user import User
from .shopping_list import ShoppingList, ShoppingListItem

# Modelos del Conversation Service
from .conversation_context import (
    Usuario, UserContext, UserInteraction, AnonymousCache, ContextChange,
    create_temporary_user, create_persistent_user
)
from .contextual_anchor import (
    ContextualAnchor, AnchorTemplate,
    create_default_anchors_for_user, get_anchor_importance_weights
)

# Exportar todos los modelos
__all__ = [
    # Modelos principales
    "Category", "Product", "Supermarket", "Store", "Price", "User", 
    "ShoppingList", "ShoppingListItem",
    
    # Modelos del Conversation Service
    "Usuario", "UserContext", "UserInteraction", "AnonymousCache", "ContextChange",
    "ContextualAnchor", "AnchorTemplate",
    
    # Funciones auxiliares
    "create_temporary_user", "create_persistent_user",
    "create_default_anchors_for_user", "get_anchor_importance_weights"
]
