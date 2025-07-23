"""
Endpoints de tiendas con nomenclatura en español y manejo de caracteres especiales
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from uuid import UUID
import time

from app.core.database import get_db
from app.services.store_service import store_service
from app.schemas.store import (
    StoreSearchResponse, StoreDetailResponse, NearbyStoresResponse,
    StoreServicesResponse, SupermarketsListResponse
)
from app.schemas.common import ErrorResponse

router = APIRouter()


@router.get(
    "/buscar-por-comuna",
    response_model=StoreSearchResponse,
    summary="Buscar tiendas por comuna",
    description="Búsqueda inteligente de tiendas por comuna con manejo de caracteres especiales (ej: Ñuñoa)",
    responses={
        200: {"description": "Tiendas encontradas exitosamente"},
        400: {"model": ErrorResponse, "description": "Parámetros de búsqueda inválidos"},
        500: {"model": ErrorResponse, "description": "Error interno del servidor"}
    }
)
async def buscar_tiendas_por_comuna(
    termino: str = Query(..., min_length=1, max_length=100, description="Término de búsqueda (comuna)"),
    limite: int = Query(50, ge=1, le=100, description="Número máximo de resultados"),
    db: Session = Depends(get_db)
):
    """
    Buscar tiendas por comuna con manejo inteligente de caracteres especiales.
    
    **Características especiales:**
    - Encuentra "Ñuñoa" escribiendo "Nunoa", "nunoa", "NUNOA" o cualquier variación
    - Búsqueda por similitud para manejar errores de tipeo
    - Normalización automática de acentos y caracteres especiales
    
    **Ejemplos de búsqueda:**
    - "Ñuñoa" → encuentra tiendas en Ñuñoa
    - "Nunoa" → encuentra tiendas en Ñuñoa
    - "Penalolen" → encuentra tiendas en Peñalolén
    - "Las Condes" → encuentra tiendas en Las Condes
    """
    try:
        start_time = time.time()
        
        stores = store_service.search_by_commune(db, termino, limite)
        
        end_time = time.time()
        response_time = int((end_time - start_time) * 1000)
        
        return {
            "tiendas": stores,
            "total": len(stores),
            "termino_busqueda": termino,
            "tiempo_respuesta_ms": response_time
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error interno al buscar tiendas: {str(e)}"
        )


@router.get(
    "/cercanas",
    response_model=NearbyStoresResponse,
    summary="Obtener tiendas cercanas",
    description="Obtener tiendas cercanas a una ubicación específica con cálculo de distancia",
    responses={
        200: {"description": "Tiendas cercanas encontradas"},
        400: {"model": ErrorResponse, "description": "Coordenadas inválidas"},
        500: {"model": ErrorResponse, "description": "Error interno del servidor"}
    }
)
async def obtener_tiendas_cercanas(
    lat: float = Query(..., ge=-90, le=90, description="Latitud"),
    lon: float = Query(..., ge=-180, le=180, description="Longitud"),
    radio_km: float = Query(10.0, ge=0.1, le=50, description="Radio de búsqueda en kilómetros"),
    tipo_supermercado: Optional[str] = Query(None, description="Tipo de supermercado (retail/mayorista)"),
    abierto_ahora: bool = Query(False, description="Solo tiendas abiertas ahora"),
    limite: int = Query(50, ge=1, le=100, description="Número máximo de resultados"),
    db: Session = Depends(get_db)
):
    """
    Obtener tiendas cercanas a una ubicación.
    
    **Funcionalidades:**
    - Cálculo preciso de distancia usando PostGIS
    - Estimación de tiempo de viaje
    - Filtrado por tipo de supermercado
    - Información de horarios y servicios
    - Ordenamiento por distancia
    
    **Parámetros:**
    - **lat/lon**: Coordenadas de referencia
    - **radio_km**: Radio de búsqueda (máximo 50km)
    - **tipo_supermercado**: "retail" o "mayorista"
    - **abierto_ahora**: Filtrar solo tiendas abiertas
    """
    try:
        # Validar tipo de supermercado
        if tipo_supermercado and tipo_supermercado not in ["retail", "mayorista"]:
            raise HTTPException(
                status_code=400,
                detail="tipo_supermercado debe ser 'retail' o 'mayorista'"
            )
        
        stores = store_service.get_nearby_stores(
            db=db,
            lat=lat,
            lon=lon,
            radio_km=radio_km,
            tipo_supermercado=tipo_supermercado,
            abierto_ahora=abierto_ahora,
            limite=limite
        )
        
        return {
            "tiendas": stores,
            "total": len(stores),
            "ubicacion_busqueda": {"lat": lat, "lon": lon},
            "radio_km": radio_km,
            "filtros_aplicados": {
                "tipo_supermercado": tipo_supermercado,
                "abierto_ahora": abierto_ahora
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error interno al obtener tiendas cercanas: {str(e)}"
        )


@router.get(
    "/{tienda_id}",
    response_model=StoreDetailResponse,
    summary="Obtener tienda por ID",
    description="Obtener información detallada de una tienda específica",
    responses={
        200: {"description": "Tienda encontrada"},
        404: {"model": ErrorResponse, "description": "Tienda no encontrada"},
        400: {"model": ErrorResponse, "description": "ID de tienda inválido"}
    }
)
async def obtener_tienda(
    tienda_id: UUID = Path(..., description="ID único de la tienda"),
    db: Session = Depends(get_db)
):
    """
    Obtener información detallada de una tienda.
    
    **Información incluida:**
    - Datos básicos de la tienda
    - Información del supermercado
    - Ubicación y coordenadas
    - Horarios de atención
    - Servicios disponibles
    - Información de contacto
    """
    try:
        store = store_service.get_store_by_id(db, tienda_id)
        
        if not store:
            raise HTTPException(
                status_code=404,
                detail=f"Tienda con ID {tienda_id} no encontrada"
            )
        
        return store
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error interno al obtener tienda: {str(e)}"
        )


@router.get(
    "/con-productos/disponibles",
    response_model=NearbyStoresResponse,
    summary="Obtener tiendas con productos específicos",
    description="Obtener tiendas que tienen productos específicos disponibles",
    responses={
        200: {"description": "Tiendas con productos encontradas"},
        400: {"model": ErrorResponse, "description": "Parámetros inválidos"}
    }
)
async def obtener_tiendas_con_productos(
    producto_ids: str = Query(..., description="IDs de productos separados por comas"),
    lat: Optional[float] = Query(None, ge=-90, le=90, description="Latitud"),
    lon: Optional[float] = Query(None, ge=-180, le=180, description="Longitud"),
    radio_km: float = Query(10.0, ge=0.1, le=50, description="Radio de búsqueda"),
    limite: int = Query(50, ge=1, le=100, description="Número máximo de resultados"),
    db: Session = Depends(get_db)
):
    """
    Obtener tiendas que tienen productos específicos disponibles.
    
    **Funcionalidades:**
    - Búsqueda por múltiples productos
    - Filtrado geográfico opcional
    - Información de disponibilidad por tienda
    - Precios promedio por tienda
    
    **Parámetros:**
    - **producto_ids**: IDs separados por comas (ej: "uuid1,uuid2,uuid3")
    - **lat/lon**: Coordenadas para filtro geográfico
    - **radio_km**: Radio de búsqueda
    """
    try:
        # Parsear IDs de productos
        try:
            product_uuids = [UUID(pid.strip()) for pid in producto_ids.split(",")]
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Formato de IDs de productos inválido. Use UUIDs separados por comas."
            )
        
        # Validar coordenadas
        if (lat is None) != (lon is None):
            raise HTTPException(
                status_code=400,
                detail="Debe proporcionar tanto latitud como longitud, o ninguna"
            )
        
        stores = store_service.get_nearby_stores(
            db=db,
            lat=lat,
            lon=lon,
            radio_km=radio_km,
            producto_ids=product_uuids,
            limite=limite
        )
        
        return {
            "tiendas": stores,
            "total": len(stores),
            "ubicacion_busqueda": {"lat": lat, "lon": lon} if lat and lon else None,
            "radio_km": radio_km,
            "filtros_aplicados": {
                "productos_solicitados": len(product_uuids)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error interno al obtener tiendas con productos: {str(e)}"
        )


@router.get(
    "/con-servicios/buscar",
    response_model=StoreServicesResponse,
    summary="Buscar tiendas con servicios específicos",
    description="Buscar tiendas que ofrecen servicios específicos (farmacia, panadería, etc.)",
    responses={
        200: {"description": "Tiendas con servicios encontradas"},
        400: {"model": ErrorResponse, "description": "Servicios inválidos"}
    }
)
async def buscar_tiendas_con_servicios(
    servicios: str = Query(..., description="Servicios separados por comas"),
    lat: Optional[float] = Query(None, ge=-90, le=90, description="Latitud"),
    lon: Optional[float] = Query(None, ge=-180, le=180, description="Longitud"),
    radio_km: float = Query(10.0, ge=0.1, le=50, description="Radio de búsqueda"),
    limite: int = Query(50, ge=1, le=100, description="Número máximo de resultados"),
    db: Session = Depends(get_db)
):
    """
    Buscar tiendas que ofrecen servicios específicos.
    
    **Servicios disponibles:**
    - farmacia
    - panaderia
    - estacionamiento
    - cajero_automatico
    - foto_copiado
    - envio_dinero
    
    **Ejemplos:**
    - servicios="farmacia" → tiendas con farmacia
    - servicios="farmacia,panaderia" → tiendas con farmacia Y panadería
    - servicios="estacionamiento" → tiendas con estacionamiento
    """
    try:
        # Parsear servicios
        services_list = [s.strip().lower() for s in servicios.split(",")]
        
        # Validar servicios
        valid_services = [
            "farmacia", "panaderia", "estacionamiento", "cajero_automatico",
            "foto_copiado", "envio_dinero", "optica", "veterinaria"
        ]
        
        invalid_services = [s for s in services_list if s not in valid_services]
        if invalid_services:
            raise HTTPException(
                status_code=400,
                detail=f"Servicios inválidos: {', '.join(invalid_services)}. "
                       f"Servicios válidos: {', '.join(valid_services)}"
            )
        
        # Validar coordenadas
        if (lat is None) != (lon is None):
            raise HTTPException(
                status_code=400,
                detail="Debe proporcionar tanto latitud como longitud, o ninguna"
            )
        
        stores = store_service.get_stores_with_services(
            db=db,
            servicios=services_list,
            lat=lat,
            lon=lon,
            radio_km=radio_km,
            limite=limite
        )
        
        return {
            "tiendas": stores,
            "servicios_solicitados": services_list,
            "total": len(stores),
            "ubicacion": {"lat": lat, "lon": lon} if lat and lon else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error interno al buscar tiendas con servicios: {str(e)}"
        )


@router.get(
    "/supermercados/lista",
    response_model=SupermarketsListResponse,
    summary="Obtener lista de supermercados",
    description="Obtener lista de todas las cadenas de supermercados disponibles",
    responses={
        200: {"description": "Supermercados obtenidos exitosamente"}
    }
)
async def obtener_supermercados(
    tipo: Optional[str] = Query(None, description="Tipo de supermercado (retail/mayorista)"),
    activos_solamente: bool = Query(True, description="Solo supermercados activos"),
    db: Session = Depends(get_db)
):
    """
    Obtener lista de supermercados disponibles.
    
    **Información incluida:**
    - Datos básicos del supermercado
    - Tipo (retail/mayorista)
    - Información de servicios
    - Número de tiendas
    - Políticas de compra mínima
    """
    try:
        # TODO: Implementar servicio de supermercados
        # Por ahora retornamos una respuesta básica
        return {
            "supermercados": [],
            "total": 0
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error interno al obtener supermercados: {str(e)}"
        )

