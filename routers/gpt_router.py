# backend/routers/gpt_router.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, constr, StrictFloat
from typing import List, Optional

from app.utils.sanitizer import sanitize_text

router = APIRouter(prefix="/api", tags=["gpt"] )

def _sanitize_and_validate(value: str) -> str:
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
async def search_products(query: str, category: Optional[str] = None):
    """Endpoint específico para que GPT busque productos"""
    try:
        query = _sanitize_and_validate(query)
        category = _sanitize_and_validate(category) if category else None
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
        sanitized_products = [_sanitize_and_validate(p) for p in request.products]
        # Tu lógica de optimización aquí
        optimization = await optimize_purchases(sanitized_products, request.location)
        
        return {
            "success": True,
            "data": optimization,
            "message": "Lista optimizada correctamente"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
