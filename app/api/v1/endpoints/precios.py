"""
Endpoints de precios con nomenclatura en español
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from uuid import UUID
import time

from fastapi_limiter import limiter
from app.core.config import settings
from app.core.database import get_db
from app.services.price_service import price_service
from app.services.product_service import product_service
from app.schemas.price import (
    PriceComparisonResponse, BestDealsResponse, PriceHistoryResponse
)
from app.schemas.common import ErrorResponse

router = APIRouter()


@router.get(
    "/comparar/{producto_id}",
    response_model=PriceComparisonResponse,
    summary="Comparar precios de un producto",
    description="Comparar precios de un producto entre diferentes tiendas con análisis detallado",
    responses={
        200: {"description": "Comparación de precios exitosa"},
        404: {"model": ErrorResponse, "description": "Producto no encontrado"},
        400: {"model": ErrorResponse, "description": "Parámetros inválidos"},
        500: {"model": ErrorResponse, "description": "Error interno del servidor"}
    }
)
@limiter.limit(
    f"{settings.RATE_LIMIT_PER_MINUTE}/minute",
    error_message="Demasiadas solicitudes, intenta nuevamente más tarde."
)
async def comparar_precios(
    producto_id: UUID = Path(..., description="ID único del producto"),
    lat: Optional[float] = Query(None, ge=-90, le=90, description="Latitud"),
    lon: Optional[float] = Query(None, ge=-180, le=180, description="Longitud"),
    radio_km: float = Query(10.0, ge=0.1, le=50, description="Radio de búsqueda en kilómetros"),
    incluir_mayoristas: bool = Query(False, description="Incluir supermercados mayoristas"),
    db: Session = Depends(get_db)
):
    """
    Comparar precios de un producto entre diferentes tiendas.
    
    **Funcionalidades:**
    - Comparación de precios en tiempo real
    - Cálculo de distancias y tiempos estimados
    - Identificación de mejores ofertas
    - Estadísticas de precios (min, max, promedio)
    - Recomendaciones inteligentes de compra
    
    **Información incluida:**
    - Precios normales y con descuento
    - Porcentajes de descuento
    - Disponibilidad de stock
    - Distancia y tiempo estimado
    - Promociones vigentes
    
    **Ejemplo de uso:**
    ```
    GET /api/v1/precios/comparar/123e4567-e89b-12d3-a456-426614174000?lat=-33.4489&lon=-70.6693&radio_km=15
    ```
    """
    try:
        # Validar coordenadas
        if (lat is None) != (lon is None):
            raise HTTPException(
                status_code=400,
                detail="Debe proporcionar tanto latitud como longitud, o ninguna"
            )
        
        comparison = price_service.compare_prices(
            db=db,
            product_id=producto_id,
            lat=lat,
            lon=lon,
            radio_km=radio_km,
            incluir_mayoristas=incluir_mayoristas
        )

        # Verificar si se encontró el producto
        if "error" in comparison:
            raise HTTPException(
                status_code=404,
                detail=comparison["error"]
            )

        # Sugerir marca alternativa cuando no hay stock disponible
        if not comparison.get("precios"):
            alternativa = product_service.get_alternative_brand(db, producto_id)
            if alternativa:
                comparison["marca_sugerida"] = alternativa
                comparison["explicacion"] = f"Producto sin stock disponible. Se sugiere marca {alternativa}."

        return comparison
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error interno al comparar precios: {str(e)}"
        )


@router.get(
    "/mejores-ofertas",
    response_model=BestDealsResponse,
    summary="Obtener mejores ofertas",
    description="Obtener las mejores ofertas disponibles con descuentos significativos",
    responses={
        200: {"description": "Mejores ofertas obtenidas exitosamente"},
        400: {"model": ErrorResponse, "description": "Parámetros inválidos"},
        500: {"model": ErrorResponse, "description": "Error interno del servidor"}
    }
)
async def obtener_mejores_ofertas(
    min_descuento: float = Query(20.0, ge=0, le=100, description="Descuento mínimo en porcentaje"),
    lat: Optional[float] = Query(None, ge=-90, le=90, description="Latitud"),
    lon: Optional[float] = Query(None, ge=-180, le=180, description="Longitud"),
    radio_km: float = Query(10.0, ge=0.1, le=50, description="Radio de búsqueda en kilómetros"),
    limite: int = Query(50, ge=1, le=100, description="Número máximo de ofertas"),
    db: Session = Depends(get_db)
):
    """
    Obtener las mejores ofertas disponibles.
    
    **Características:**
    - Filtrado por descuento mínimo
    - Búsqueda geográfica opcional
    - Ordenamiento por porcentaje de descuento
    - Información detallada de cada oferta
    - Cálculo de ahorros totales
    
    **Criterios de selección:**
    - Descuento igual o mayor al mínimo especificado
    - Stock disponible
    - Promociones vigentes
    - Distancia dentro del radio especificado
    
    **Información por oferta:**
    - Producto y marca
    - Precio normal vs precio con descuento
    - Porcentaje y monto de ahorro
    - Tienda y ubicación
    - Distancia y tiempo estimado
    """
    try:
        # Validar coordenadas
        if (lat is None) != (lon is None):
            raise HTTPException(
                status_code=400,
                detail="Debe proporcionar tanto latitud como longitud, o ninguna"
            )
        
        deals = price_service.get_best_deals(
            db=db,
            min_descuento=min_descuento,
            lat=lat,
            lon=lon,
            radio_km=radio_km,
            limite=limite
        )
        
        # Calcular ahorro total disponible
        total_savings = sum(deal.get("ahorro", 0) for deal in deals)
        
        return {
            "ofertas": deals,
            "total_ofertas": len(deals),
            "descuento_minimo": min_descuento,
            "ubicacion": {"lat": lat, "lon": lon} if lat and lon else None,
            "ahorro_total_disponible": total_savings
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error interno al obtener mejores ofertas: {str(e)}"
        )


@router.get(
    "/historial/{producto_id}/{tienda_id}",
    response_model=PriceHistoryResponse,
    summary="Obtener historial de precios",
    description="Obtener historial de precios de un producto en una tienda específica",
    responses={
        200: {"description": "Historial obtenido exitosamente"},
        404: {"model": ErrorResponse, "description": "Producto o tienda no encontrados"},
        400: {"model": ErrorResponse, "description": "Parámetros inválidos"},
        500: {"model": ErrorResponse, "description": "Error interno del servidor"}
    }
)
async def obtener_historial_precios(
    producto_id: UUID = Path(..., description="ID único del producto"),
    tienda_id: UUID = Path(..., description="ID único de la tienda"),
    dias: int = Query(30, ge=1, le=365, description="Número de días de historial"),
    db: Session = Depends(get_db)
):
    """
    Obtener historial de precios de un producto en una tienda.
    
    **Funcionalidades:**
    - Historial detallado por fecha
    - Estadísticas del período
    - Análisis de variaciones de precio
    - Información de descuentos históricos
    - Tendencias de precios
    
    **Estadísticas incluidas:**
    - Precio mínimo, máximo y promedio del período
    - Variación total de precios
    - Días con descuentos
    - Descuento promedio
    - Número total de registros
    
    **Casos de uso:**
    - Análisis de tendencias de precios
    - Identificación de patrones de descuentos
    - Validación de ofertas actuales
    - Planificación de compras
    """
    try:
        history = price_service.get_price_history(
            db=db,
            product_id=producto_id,
            store_id=tienda_id,
            dias=dias
        )
        
        # Verificar si se encontraron el producto y la tienda
        if "error" in history:
            raise HTTPException(
                status_code=404,
                detail=history["error"]
            )
        
        return history
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error interno al obtener historial: {str(e)}"
        )


@router.get(
    "/tendencias/producto/{producto_id}",
    summary="Obtener tendencias de precio",
    description="Obtener tendencias de precio de un producto en diferentes comunas",
    responses={
        200: {"description": "Tendencias obtenidas exitosamente"},
        404: {"model": ErrorResponse, "description": "Producto no encontrado"}
    }
)
async def obtener_tendencias_precio(
    producto_id: UUID = Path(..., description="ID único del producto"),
    db: Session = Depends(get_db)
):
    """
    Obtener tendencias de precio por comuna.
    
    **Información incluida:**
    - Precio promedio por comuna
    - Precio mínimo y máximo por comuna
    - Número de tiendas por comuna
    - Ranking de comunas por precio
    
    **Utilidad:**
    - Identificar comunas con mejores precios
    - Análisis geográfico de precios
    - Planificación de rutas de compra
    """
    try:
        # TODO: Implementar análisis de tendencias
        # Por ahora retornamos respuesta básica
        return {
            "producto_id": str(producto_id),
            "tendencias_por_comuna": [],
            "mensaje": "Funcionalidad en desarrollo"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error interno al obtener tendencias: {str(e)}"
        )


@router.get(
    "/alertas/precio",
    summary="Obtener alertas de precio",
    description="Obtener alertas de precio configuradas por el usuario",
    responses={
        200: {"description": "Alertas obtenidas exitosamente"}
    }
)
async def obtener_alertas_precio(
    activas_solamente: bool = Query(True, description="Solo alertas activas"),
    db: Session = Depends(get_db)
):
    """
    Obtener alertas de precio del usuario.
    
    **Funcionalidades:**
    - Lista de alertas configuradas
    - Estado de cada alerta
    - Precios objetivo vs actuales
    - Historial de activaciones
    
    **Nota:** Requiere autenticación de usuario (funcionalidad futura)
    """
    try:
        # TODO: Implementar sistema de alertas
        # Requiere autenticación de usuario
        return {
            "alertas": [],
            "total": 0,
            "mensaje": "Sistema de alertas en desarrollo - requiere autenticación"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error interno al obtener alertas: {str(e)}"
        )


@router.post(
    "/alertas/crear",
    summary="Crear alerta de precio",
    description="Crear una nueva alerta de precio para un producto",
    responses={
        201: {"description": "Alerta creada exitosamente"},
        400: {"model": ErrorResponse, "description": "Datos de alerta inválidos"}
    }
)
async def crear_alerta_precio(
    db: Session = Depends(get_db)
):
    """
    Crear alerta de precio.
    
    **Funcionalidades:**
    - Configuración de precio objetivo
    - Selección de tiendas específicas
    - Radio de búsqueda personalizable
    - Notificaciones automáticas
    
    **Nota:** Requiere autenticación de usuario (funcionalidad futura)
    """
    try:
        # TODO: Implementar creación de alertas
        # Requiere autenticación de usuario
        return {
            "mensaje": "Sistema de alertas en desarrollo - requiere autenticación",
            "status": "pending_implementation"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error interno al crear alerta: {str(e)}"
        )

