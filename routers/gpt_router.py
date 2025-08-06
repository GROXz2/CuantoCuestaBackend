# backend/routers/gpt_router.py

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field, constr, StrictFloat

from auth import verify_gpt_token
from app.main import ERROR_MESSAGES
from app.utils.sanitizer import sanitize_text

router = APIRouter(prefix="/api", tags=["gpt"])

logger = logging.getLogger(__name__)


def _sanitize_and_validate(value: str) -> str:
    """Aplica el sanitizer y valida que no quede vacío."""
    sanitized = sanitize_text(value)
    if not sanitized:
        raise HTTPException(status_code=422, detail="Invalid input")
    return sanitized


class SearchRequest(BaseModel):
    query: constr(strict=True, min_length=1, max_length=100, pattern=r"^[\w\s-]+$")
    category: Optional[constr(strict=True, max_length=50, pattern=r"^[\w\s-]+$")] = None


class Location(BaseModel):
    lat: StrictFloat = Field(..., ge=-90, le=90)
    lon: StrictFloat = Field(..., ge=-180, le=180)


class OptimizeRequest(BaseModel):
    products: List[constr(strict=True, min_length=1, max_length=100, pattern=r"^[\w\s-]+$")]
    location: Optional[Location] = None


@router.get("/products/search")
async def search_products(
    query: str,
    category: Optional[str] = None,
    token: str = Depends(verify_gpt_token),
):
    """Endpoint específico para que GPT busque productos (requiere token)."""
    try:
        q = _sanitize_and_validate(query)
        c = _sanitize_and_validate(category) if category else None

        products = await search_products_in_db(q, c)
        return {
            "success": True,
            "data": products,
            "message": f"Encontrados {len(products)} productos para '{q}'",
        }
    except HTTPException as he:
        # pasa 422 de sanitización o errores controlados
        raise he
    except Exception:
        logger.exception("Error en search_products")
        raise HTTPException(status_code=500, detail=ERROR_MESSAGES["PRODUCT_SEARCH_ERROR"])


@router.post("/optimize")
async def optimize_shopping_list(
    request: OptimizeRequest,
    token: str = Depends(verify_gpt_token),
):
    """Endpoint para optimizar lista de compras (requiere token)."""
    try:
        sanitized_products = [_sanitize_and_validate(p) for p in request.products]
        optimization = await optimize_purchases(sanitized_products, request.location)
        return {
            "success": True,
            "data": optimization,
            "message": "Lista optimizada correctamente",
        }
    except HTTPException as he:
        raise he
    except Exception:
        logger.exception("Error en optimize_shopping_list")
        raise HTTPException(status_code=500, detail=ERROR_MESSAGES["OPTIMIZE_ERROR"])


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

        req = OptimizationRequest(productos=products, ubicacion=location)
        return await service.optimize_shopping_list(req)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error optimizando compras: {e}")
