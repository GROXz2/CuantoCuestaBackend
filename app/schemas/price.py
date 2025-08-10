"""
Schemas para precios con nomenclatura en español
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime

from app.schemas.common import (
    ProductBasicInfo, StoreBasicInfo, StatisticsResponse, 
    RecommendationResponse, Config
)


class PriceComparisonRequest(BaseModel):
    """Request para comparación de precios"""
    producto_id: UUID = Field(..., description="ID del producto a comparar")
    lat: Optional[float] = Field(None, ge=-90, le=90, description="Latitud")
    lon: Optional[float] = Field(None, ge=-180, le=180, description="Longitud")
    radio_km: float = Field(10.0, ge=0.1, le=50, description="Radio de búsqueda en kilómetros")
    incluir_mayoristas: bool = Field(False, description="Incluir supermercados mayoristas")
    
    class Config(Config):
        json_schema_extra = {
            "example": {
                "producto_id": "123e4567-e89b-12d3-a456-426614174000",
                "lat": -33.4489,
                "lon": -70.6693,
                "radio_km": 10.0,
                "incluir_mayoristas": False
            }
        }


class PriceDetailResponse(BaseModel):
    """Respuesta detallada de precio"""
    tienda_id: str = Field(..., description="ID de la tienda")
    supermercado: str = Field(..., description="Nombre del supermercado")
    tienda_nombre: str = Field(..., description="Nombre de la tienda")
    comuna: str = Field(..., description="Comuna de la tienda")
    direccion: str = Field(..., description="Dirección de la tienda")
    telefono: Optional[str] = Field(None, description="Teléfono de la tienda")
    precio_normal: float = Field(..., description="Precio normal del producto")
    precio_descuento: Optional[float] = Field(None, description="Precio con descuento")
    porcentaje_descuento: float = Field(0, description="Porcentaje de descuento")
    precio_efectivo: float = Field(..., description="Precio efectivo (con descuento si aplica)")
    stock_disponible: bool = Field(True, description="Si el producto está disponible")
    estado_stock: str = Field(..., description="Estado del stock (available/low_stock/out_of_stock)")
    descripcion_promocion: Optional[str] = Field(None, description="Descripción de la promoción")
    fecha_actualizacion: Optional[str] = Field(None, description="Fecha de última actualización")
    logo_supermercado: Optional[str] = Field(None, description="URL del logo del supermercado")
    distancia_km: Optional[float] = Field(None, description="Distancia en kilómetros")
    tiempo_estimado_min: Optional[int] = Field(None, description="Tiempo estimado en minutos")
    
    class Config(Config):
        json_schema_extra = {
            "example": {
                "tienda_id": "123e4567-e89b-12d3-a456-426614174000",
                "supermercado": "Jumbo",
                "tienda_nombre": "Jumbo Ñuñoa",
                "comuna": "Ñuñoa",
                "precio_normal": 1250,
                "precio_descuento": 990,
                "porcentaje_descuento": 20.8,
                "precio_efectivo": 990,
                "stock_disponible": True,
                "distancia_km": 2.5,
                "tiempo_estimado_min": 8
            }
        }


class PriceComparisonResponse(BaseModel):
    """Respuesta de comparación de precios"""
    producto: ProductBasicInfo = Field(..., description="Información del producto")
    precios: List[PriceDetailResponse] = Field(..., description="Lista de precios en diferentes tiendas")
    estadisticas: StatisticsResponse = Field(..., description="Estadísticas de precios")
    recomendacion: str = Field(..., description="Recomendación de compra")
    ahorro_maximo: float = Field(..., description="Máximo ahorro posible")
    filtros_aplicados: Dict[str, Any] = Field(..., description="Filtros aplicados en la búsqueda")
    marca_sugerida: Optional[str] = Field(
        None, description="Marca alternativa sugerida cuando no hay stock"
    )
    explicacion: Optional[str] = Field(
        None, description="Explicación de la sugerencia de marca"
    )
    
    class Config(Config):
        json_schema_extra = {
            "example": {
                "producto": {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "nombre": "Pan Integral Bimbo",
                    "marca": "Bimbo"
                },
                "precios": [
                    {
                        "tienda_nombre": "Jumbo Ñuñoa",
                        "precio_normal": 1250,
                        "precio_descuento": 990,
                        "porcentaje_descuento": 20.8,
                        "distancia_km": 2.5
                    }
                ],
                "ahorro_maximo": 260,
                "recomendacion": "Mejor precio en Jumbo Ñuñoa con 20.8% descuento"
            }
        }


class BestDealsRequest(BaseModel):
    """Request para mejores ofertas"""
    min_descuento: float = Field(20.0, ge=0, le=100, description="Descuento mínimo en porcentaje")
    lat: Optional[float] = Field(None, ge=-90, le=90, description="Latitud")
    lon: Optional[float] = Field(None, ge=-180, le=180, description="Longitud")
    radio_km: float = Field(10.0, ge=0.1, le=50, description="Radio de búsqueda")
    limite: int = Field(50, ge=1, le=100, description="Número máximo de ofertas")
    
    class Config(Config):
        json_schema_extra = {
            "example": {
                "min_descuento": 25.0,
                "lat": -33.4489,
                "lon": -70.6693,
                "radio_km": 15.0,
                "limite": 30
            }
        }


class DealResponse(BaseModel):
    """Respuesta de oferta individual"""
    producto: ProductBasicInfo = Field(..., description="Información del producto")
    precio_normal: float = Field(..., description="Precio normal")
    precio_descuento: float = Field(..., description="Precio con descuento")
    porcentaje_descuento: float = Field(..., description="Porcentaje de descuento")
    ahorro: float = Field(..., description="Cantidad de ahorro en pesos")
    tienda: StoreBasicInfo = Field(..., description="Información de la tienda")
    descripcion_promocion: Optional[str] = Field(None, description="Descripción de la promoción")
    distancia_km: Optional[float] = Field(None, description="Distancia en kilómetros")
    tiempo_estimado_min: Optional[int] = Field(None, description="Tiempo estimado en minutos")
    
    class Config(Config):
        pass


class BestDealsResponse(BaseModel):
    """Respuesta de mejores ofertas"""
    ofertas: List[DealResponse] = Field(..., description="Lista de mejores ofertas")
    total_ofertas: int = Field(..., description="Total de ofertas encontradas")
    descuento_minimo: float = Field(..., description="Descuento mínimo aplicado")
    ubicacion: Optional[Dict[str, float]] = Field(None, description="Ubicación utilizada")
    ahorro_total_disponible: float = Field(..., description="Ahorro total disponible")
    
    class Config(Config):
        pass


class PriceHistoryRequest(BaseModel):
    """Request para historial de precios"""
    producto_id: UUID = Field(..., description="ID del producto")
    tienda_id: UUID = Field(..., description="ID de la tienda")
    dias: int = Field(30, ge=1, le=365, description="Número de días de historial")
    
    class Config(Config):
        json_schema_extra = {
            "example": {
                "producto_id": "123e4567-e89b-12d3-a456-426614174000",
                "tienda_id": "456e7890-e89b-12d3-a456-426614174000",
                "dias": 30
            }
        }


class PriceHistoryEntry(BaseModel):
    """Entrada de historial de precios"""
    fecha: str = Field(..., description="Fecha del precio")
    precio_normal: float = Field(..., description="Precio normal")
    precio_descuento: Optional[float] = Field(None, description="Precio con descuento")
    porcentaje_descuento: float = Field(0, description="Porcentaje de descuento")
    precio_efectivo: float = Field(..., description="Precio efectivo")
    estado_stock: str = Field(..., description="Estado del stock")
    fecha_hora_actualizacion: str = Field(..., description="Timestamp de actualización")
    
    class Config(Config):
        pass


class PriceHistoryStatistics(BaseModel):
    """Estadísticas del historial de precios"""
    precio_minimo_periodo: float = Field(..., description="Precio mínimo en el período")
    precio_maximo_periodo: float = Field(..., description="Precio máximo en el período")
    precio_promedio_periodo: float = Field(..., description="Precio promedio en el período")
    variacion_precio: float = Field(..., description="Variación de precio")
    total_registros: int = Field(..., description="Total de registros")
    dias_con_descuento: int = Field(..., description="Días con descuento")
    descuento_promedio: float = Field(..., description="Descuento promedio")
    
    class Config(Config):
        pass


class PriceHistoryResponse(BaseModel):
    """Respuesta de historial de precios"""
    producto: ProductBasicInfo = Field(..., description="Información del producto")
    tienda: StoreBasicInfo = Field(..., description="Información de la tienda")
    historial: List[PriceHistoryEntry] = Field(..., description="Historial de precios")
    estadisticas: PriceHistoryStatistics = Field(..., description="Estadísticas del período")
    periodo_dias: int = Field(..., description="Período analizado en días")
    
    class Config(Config):
        pass


class PriceAlertRequest(BaseModel):
    """Request para alerta de precio"""
    producto_id: UUID = Field(..., description="ID del producto")
    precio_objetivo: float = Field(..., ge=0, description="Precio objetivo para la alerta")
    tienda_ids: Optional[List[UUID]] = Field(None, description="IDs de tiendas específicas")
    radio_km: float = Field(10.0, ge=0.1, le=50, description="Radio de búsqueda")
    activa: bool = Field(True, description="Si la alerta está activa")
    
    class Config(Config):
        json_schema_extra = {
            "example": {
                "producto_id": "123e4567-e89b-12d3-a456-426614174000",
                "precio_objetivo": 800,
                "radio_km": 15.0,
                "activa": True
            }
        }


class PriceAlertResponse(BaseModel):
    """Respuesta de alerta de precio"""
    id: str = Field(..., description="ID de la alerta")
    producto: ProductBasicInfo = Field(..., description="Información del producto")
    precio_objetivo: float = Field(..., description="Precio objetivo")
    precio_actual_mejor: Optional[float] = Field(None, description="Mejor precio actual")
    diferencia: Optional[float] = Field(None, description="Diferencia con precio objetivo")
    alerta_activada: bool = Field(False, description="Si la alerta se ha activado")
    fecha_creacion: str = Field(..., description="Fecha de creación")
    activa: bool = Field(True, description="Si la alerta está activa")
    
    class Config(Config):
        pass

