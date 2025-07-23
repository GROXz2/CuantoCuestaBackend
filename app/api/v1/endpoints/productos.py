"""
Endpoints de productos con nomenclatura en español
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from uuid import UUID
import time

from app.core.database import get_db
from app.services.product_service import product_service
from app.schemas.product import (
    ProductSearchResponse, ProductDetailResponse, ProductBarcodeRequest,
    PopularProductsResponse, ProductDiscountsResponse, CategoriesListResponse
)
from app.schemas.common import ErrorResponse

router = APIRouter()


@router.get(
    "/buscar",
    response_model=ProductSearchResponse,
    summary="Buscar productos",
    description="Búsqueda inteligente de productos con filtros avanzados y geolocalización",
    responses={
        200: {"description": "Productos encontrados exitosamente"},
        400: {"model": ErrorResponse, "description": "Parámetros de búsqueda inválidos"},
        500: {"model": ErrorResponse, "description": "Error interno del servidor"}
    }
)
async def buscar_productos(
    q: str = Query(..., min_length=1, max_length=100, description="Término de búsqueda"),
    categoria_id: Optional[UUID] = Query(None, description="ID de categoría para filtrar"),
    precio_min: Optional[float] = Query(None, ge=0, description="Precio mínimo"),
    precio_max: Optional[float] = Query(None, ge=0, description="Precio máximo"),
    lat: Optional[float] = Query(None, ge=-90, le=90, description="Latitud"),
    lon: Optional[float] = Query(None, ge=-180, le=180, description="Longitud"),
    radio_km: float = Query(10.0, ge=0.1, le=50, description="Radio de búsqueda en km"),
    limite: int = Query(50, ge=1, le=100, description="Número máximo de resultados"),
    skip: int = Query(0, ge=0, description="Número de resultados a omitir"),
    db: Session = Depends(get_db)
):
    """
    Buscar productos con filtros avanzados.
    
    - **q**: Término de búsqueda (nombre, marca, descripción)
    - **categoria_id**: Filtrar por categoría específica
    - **precio_min/precio_max**: Rango de precios
    - **lat/lon**: Coordenadas para búsqueda geográfica
    - **radio_km**: Radio de búsqueda en kilómetros
    - **limite**: Máximo número de resultados
    """
    try:
        start_time = time.time()
        
        # Validar rango de precios
        if precio_min is not None and precio_max is not None and precio_min >= precio_max:
            raise HTTPException(
                status_code=400,
                detail="El precio mínimo debe ser menor que el precio máximo"
            )
        
        # Validar coordenadas (ambas o ninguna)
        if (lat is None) != (lon is None):
            raise HTTPException(
                status_code=400,
                detail="Debe proporcionar tanto latitud como longitud, o ninguna"
            )
        
        # Realizar búsqueda
        result = product_service.search_products(
            db=db,
            search_term=q,
            category_id=categoria_id,
            precio_min=precio_min,
            precio_max=precio_max,
            lat=lat,
            lon=lon,
            radio_km=radio_km,
            limite=limite,
            skip=skip
        )
        
        # Agregar tiempo de respuesta
        end_time = time.time()
        result["tiempo_respuesta_ms"] = int((end_time - start_time) * 1000)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error interno al buscar productos: {str(e)}"
        )


@router.get(
    "/{producto_id}",
    response_model=ProductDetailResponse,
    summary="Obtener producto por ID",
    description="Obtener información detallada de un producto específico",
    responses={
        200: {"description": "Producto encontrado"},
        404: {"model": ErrorResponse, "description": "Producto no encontrado"},
        400: {"model": ErrorResponse, "description": "ID de producto inválido"}
    }
)
async def obtener_producto(
    producto_id: UUID = Path(..., description="ID único del producto"),
    db: Session = Depends(get_db)
):
    """
    Obtener información detallada de un producto por su ID.
    
    - **producto_id**: ID único del producto
    """
    try:
        product = product_service.get_product_by_id(db, producto_id)
        
        if not product:
            raise HTTPException(
                status_code=404,
                detail=f"Producto con ID {producto_id} no encontrado"
            )
        
        return product
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error interno al obtener producto: {str(e)}"
        )


@router.get(
    "/populares/lista",
    response_model=PopularProductsResponse,
    summary="Obtener productos populares",
    description="Obtener lista de productos más populares basado en actividad de precios",
    responses={
        200: {"description": "Productos populares obtenidos exitosamente"}
    }
)
async def obtener_productos_populares(
    limite: int = Query(20, ge=1, le=100, description="Número máximo de productos"),
    db: Session = Depends(get_db)
):
    """
    Obtener productos más populares.
    
    Los productos se ordenan por popularidad basada en:
    - Número de tiendas que los venden
    - Frecuencia de actualización de precios
    - Actividad de búsqueda
    """
    try:
        products = product_service.get_popular_products(db, limite)
        
        return {
            "productos": products,
            "criterio": "popularidad",
            "limite": limite
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error interno al obtener productos populares: {str(e)}"
        )


@router.get(
    "/ofertas/descuentos",
    response_model=ProductDiscountsResponse,
    summary="Obtener productos con descuentos",
    description="Obtener productos que tienen descuentos significativos",
    responses={
        200: {"description": "Productos con descuentos obtenidos exitosamente"}
    }
)
async def obtener_productos_con_descuentos(
    min_descuento: float = Query(10.0, ge=0, le=100, description="Descuento mínimo en porcentaje"),
    lat: Optional[float] = Query(None, ge=-90, le=90, description="Latitud"),
    lon: Optional[float] = Query(None, ge=-180, le=180, description="Longitud"),
    radio_km: float = Query(10.0, ge=0.1, le=50, description="Radio de búsqueda en km"),
    limite: int = Query(50, ge=1, le=100, description="Número máximo de productos"),
    db: Session = Depends(get_db)
):
    """
    Obtener productos con descuentos significativos.
    
    - **min_descuento**: Porcentaje mínimo de descuento
    - **lat/lon**: Coordenadas para filtrar por ubicación
    - **radio_km**: Radio de búsqueda en kilómetros
    - **limite**: Máximo número de productos
    """
    try:
        # Validar coordenadas
        if (lat is None) != (lon is None):
            raise HTTPException(
                status_code=400,
                detail="Debe proporcionar tanto latitud como longitud, o ninguna"
            )
        
        products = product_service.get_products_with_discounts(
            db=db,
            min_descuento=min_descuento,
            lat=lat,
            lon=lon,
            radio_km=radio_km,
            limite=limite
        )
        
        return {
            "productos": products,
            "descuento_minimo": min_descuento,
            "ubicacion": {"lat": lat, "lon": lon} if lat and lon else None,
            "total_ofertas": len(products)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error interno al obtener productos con descuentos: {str(e)}"
        )


@router.post(
    "/buscar-por-codigo",
    response_model=ProductDetailResponse,
    summary="Buscar producto por código de barras",
    description="Buscar un producto específico usando su código de barras",
    responses={
        200: {"description": "Producto encontrado"},
        404: {"model": ErrorResponse, "description": "Producto no encontrado"},
        400: {"model": ErrorResponse, "description": "Código de barras inválido"}
    }
)
async def buscar_por_codigo_barras(
    request: ProductBarcodeRequest,
    db: Session = Depends(get_db)
):
    """
    Buscar producto por código de barras.
    
    - **codigo_barras**: Código de barras del producto (8-20 caracteres)
    """
    try:
        product = product_service.get_product_by_barcode(db, request.codigo_barras)
        
        if not product:
            raise HTTPException(
                status_code=404,
                detail=f"No se encontró producto con código de barras {request.codigo_barras}"
            )
        
        return product
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error interno al buscar por código de barras: {str(e)}"
        )


@router.get(
    "/categorias/lista",
    response_model=CategoriesListResponse,
    summary="Obtener categorías de productos",
    description="Obtener lista de todas las categorías de productos disponibles",
    responses={
        200: {"description": "Categorías obtenidas exitosamente"}
    }
)
async def obtener_categorias(
    incluir_vacias: bool = Query(False, description="Incluir categorías sin productos"),
    db: Session = Depends(get_db)
):
    """
    Obtener lista de categorías de productos.
    
    - **incluir_vacias**: Si incluir categorías que no tienen productos
    """
    try:
        # TODO: Implementar servicio de categorías
        # Por ahora retornamos una respuesta básica
        return {
            "categorias": [],
            "total": 0
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error interno al obtener categorías: {str(e)}"
        )

