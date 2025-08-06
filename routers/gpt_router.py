# backend/routers/gpt_router.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(prefix="/api", tags=["gpt"] )

class SearchRequest(BaseModel):
    query: str
    category: Optional[str] = None

class OptimizeRequest(BaseModel):
    products: List[str]
    location: Optional[dict] = None

@router.get("/products/search")
async def search_products(query: str, category: Optional[str] = None):
    """Endpoint específico para que GPT busque productos"""
    try:
        # Tu lógica de búsqueda aquí
        products = await search_products_in_db(query, category)
        
        return {
            "success": True,
            "data": products,
            "message": f"Encontrados {len(products)} productos para '{query}'"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/optimize")
async def optimize_shopping_list(request: OptimizeRequest):
    """Endpoint para optimizar lista de compras"""
    try:
        # Tu lógica de optimización aquí
        optimization = await optimize_purchases(request.products, request.location)
        
        return {
            "success": True,
            "data": optimization,
            "message": "Lista optimizada correctamente"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def search_products_in_db(query: str, category: Optional[str] = None):
    """Search products using the product service."""
    try:
        from uuid import UUID
        from db import SessionLocal
        from app.services.product_service import product_service

        db = SessionLocal()
        try:
            category_id = UUID(category) if category else None
            result = product_service.search_products(
                db=db,
                search_term=query,
                category_id=category_id,
                limite=50,
                skip=0,
            )
            return result.get("productos", [])
        finally:
            db.close()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error buscando productos: {e}")


async def optimize_purchases(products: List[str], location: Optional[dict] = None):
    """Optimize a shopping list using the optimization service."""
    try:
        from app.services.optimization_service import OptimizationService
        from app.services.scoring_service import ScoringService
        from app.services.user_profile_service import UserProfileService
        from app.services.cache_service import CacheService
        from app.utils.distance_calculator import DistanceCalculator
        from app.utils.route_optimizer import RouteOptimizer
        from app.utils.price_analyzer import PriceAnalyzer
        from app.schemas.optimization import OptimizationRequest

        distance_calculator = DistanceCalculator()
        scoring_service = ScoringService(distance_calculator)
        user_profile_service = UserProfileService()
        cache_service = CacheService()
        route_optimizer = RouteOptimizer(distance_calculator)
        price_analyzer = PriceAnalyzer()

        service = OptimizationService(
            scoring_service=scoring_service,
            user_profile_service=user_profile_service,
            cache_service=cache_service,
            distance_calculator=distance_calculator,
            route_optimizer=route_optimizer,
            price_analyzer=price_analyzer,
        )

        request = OptimizationRequest(productos=products, ubicacion=location)
        result = await service.optimize_shopping_list(request)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error optimizando compras: {e}")
