# backend/routers/gpt_router.py
import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from auth import verify_gpt_token
from app.main import ERROR_MESSAGES

router = APIRouter(prefix="/api", tags=["gpt"])

logger = logging.getLogger(__name__)

class SearchRequest(BaseModel):
    query: str
    category: Optional[str] = None

class OptimizeRequest(BaseModel):
    products: List[str]
    location: Optional[dict] = None

@router.get("/products/search")
async def search_products(
    query: str,
    category: Optional[str] = None,
    token: str = Depends(verify_gpt_token),
):
    """Endpoint específico para que GPT busque productos"""
    try:
        # Tu lógica de búsqueda aquí
        products = await search_products_in_db(query, category)

        return {
            "success": True,
            "data": products,
            "message": f"Encontrados {len(products)} productos para '{query}'",
        }
    except Exception:
        logger.exception("Error en search_products")
        raise HTTPException(status_code=500, detail=ERROR_MESSAGES["PRODUCT_SEARCH_ERROR"])

@router.post("/optimize")
async def optimize_shopping_list(
    request: OptimizeRequest,
    token: str = Depends(verify_gpt_token),
):
    """Endpoint para optimizar lista de compras"""
    try:
        # Tu lógica de optimización aquí
        optimization = await optimize_purchases(request.products, request.location)

        return {
            "success": True,
            "data": optimization,
            "message": "Lista optimizada correctamente",
        }
    except Exception:
        logger.exception("Error en optimize_shopping_list")
        raise HTTPException(status_code=500, detail=ERROR_MESSAGES["OPTIMIZE_ERROR"])
