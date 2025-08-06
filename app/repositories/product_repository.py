"""
Repositorio de productos con búsqueda avanzada
"""
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_, text
from sqlalchemy.sql import select

from app.models.product import Product
from app.models.category import Category
from app.repositories.base_repository import BaseRepository
from app.utils.sanitizer import sanitize_text


class ProductRepository(BaseRepository[Product, dict, dict]):
    """Repositorio de productos con funcionalidades específicas"""
    
    def __init__(self):
        super().__init__(Product)
    
    def search_products(
        self,
        db: Session,
        search_term: str,
        category_id: Optional[UUID] = None,
        limit: int = 50,
        skip: int = 0
    ) -> List[Product]:
        """
        Búsqueda inteligente de productos usando texto completo y similitud
        """
        search_term = sanitize_text(search_term)
        if not search_term:
            raise ValueError("search_term")
        query = db.query(Product).join(Category)
        
        # Filtrar solo productos activos
        query = query.filter(Product.is_active == True)
        
        # Filtrar por categoría si se especifica
        if category_id:
            query = query.filter(Product.category_id == category_id)
        
        # Búsqueda por texto usando múltiples estrategias
        if search_term:
            search_conditions = []
            
            # 1. Búsqueda de texto completo usando tsvector
            search_conditions.append(
                Product.search_vector.match(search_term)
            )
            
            # 2. Búsqueda por similitud en nombre
            search_conditions.append(
                func.similarity(Product.name, search_term) > 0.3
            )
            
            # 3. Búsqueda por similitud en marca
            search_conditions.append(
                func.similarity(Product.brand, search_term) > 0.3
            )
            
            # 4. Búsqueda ILIKE para coincidencias parciales
            search_conditions.append(
                Product.name.ilike(f'%{search_term}%')
            )
            search_conditions.append(
                Product.brand.ilike(f'%{search_term}%')
            )
            
            # Combinar todas las condiciones con OR
            query = query.filter(or_(*search_conditions))
            
            # Ordenar por relevancia
            query = query.order_by(
                func.greatest(
                    func.similarity(Product.name, search_term),
                    func.similarity(Product.brand, search_term)
                ).desc(),
                Product.name
            )
        else:
            # Sin término de búsqueda, ordenar alfabéticamente
            query = query.order_by(Product.name)
        
        return query.offset(skip).limit(limit).all()
    
    def get_by_barcode(self, db: Session, barcode: str) -> Optional[Product]:
        """Obtener producto por código de barras"""
        return db.query(Product).filter(
            Product.barcode == barcode,
            Product.is_active == True
        ).first()
    
    def get_by_category(
        self, 
        db: Session, 
        category_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[Product]:
        """Obtener productos por categoría"""
        return db.query(Product).filter(
            Product.category_id == category_id,
            Product.is_active == True
        ).offset(skip).limit(limit).all()
    
    def get_by_brand(
        self, 
        db: Session, 
        brand: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Product]:
        """Obtener productos por marca"""
        brand = sanitize_text(brand)
        if not brand:
            raise ValueError("brand")
        return db.query(Product).filter(
            Product.brand.ilike(f'%{brand}%'),
            Product.is_active == True
        ).offset(skip).limit(limit).all()
    
    def get_popular_products(
        self, 
        db: Session, 
        limit: int = 20
    ) -> List[Product]:
        """
        Obtener productos populares basado en cantidad de precios registrados
        """
        from app.models.price import Price
        
        return db.query(Product).join(Price).filter(
            Product.is_active == True
        ).group_by(Product.id).order_by(
            func.count(Price.id).desc()
        ).limit(limit).all()
    
    def get_products_with_discounts(
        self, 
        db: Session,
        min_discount_percentage: float = 10.0,
        limit: int = 50
    ) -> List[Product]:
        """
        Obtener productos con descuentos significativos
        """
        from app.models.price import Price
        
        return db.query(Product).join(Price).filter(
            Product.is_active == True,
            Price.is_active == True,
            Price.discount_percentage >= min_discount_percentage
        ).distinct().limit(limit).all()
    
    def search_by_similarity(
        self,
        db: Session,
        search_term: str,
        threshold: float = 0.3,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Búsqueda por similitud con scoring
        """
        search_term = sanitize_text(search_term)
        if not search_term:
            raise ValueError("search_term")
        query = text("""
            SELECT 
                p.id,
                p.name,
                p.brand,
                c.name as category_name,
                GREATEST(
                    similarity(p.name, :search_term),
                    similarity(p.brand, :search_term)
                ) as similarity_score
            FROM products.products p
            JOIN products.categories c ON p.category_id = c.id
            WHERE 
                p.is_active = true
                AND (
                    similarity(p.name, :search_term) > :threshold
                    OR similarity(p.brand, :search_term) > :threshold
                )
            ORDER BY similarity_score DESC
            LIMIT :limit
        """)
        
        result = db.execute(query, {
            'search_term': search_term,
            'threshold': threshold,
            'limit': limit
        })
        
        return [dict(row) for row in result]
    
    def get_products_by_price_range(
        self,
        db: Session,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        limit: int = 100
    ) -> List[Product]:
        """
        Obtener productos en un rango de precios
        """
        from app.models.price import Price
        
        query = db.query(Product).join(Price).filter(
            Product.is_active == True,
            Price.is_active == True
        )
        
        if min_price is not None:
            query = query.filter(Price.normal_price >= min_price)
        
        if max_price is not None:
            query = query.filter(Price.normal_price <= max_price)
        
        return query.distinct().limit(limit).all()


# Instancia global del repositorio
product_repository = ProductRepository()

