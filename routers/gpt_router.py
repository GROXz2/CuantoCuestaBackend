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
