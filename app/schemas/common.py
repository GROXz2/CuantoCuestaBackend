"""
Schemas comunes para la API
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from uuid import UUID
from datetime import datetime
from decimal import Decimal


class ResponseBase(BaseModel):
    """Schema base para respuestas de la API"""
    success: bool = Field(True, description="Indica si la operación fue exitosa")
    message: Optional[str] = Field(None, description="Mensaje descriptivo")
    timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp de la respuesta")


class ErrorResponse(ResponseBase):
    """Schema para respuestas de error"""
    success: bool = Field(False)
    error_code: Optional[str] = Field(None, description="Código de error específico")
    details: Optional[Dict[str, Any]] = Field(None, description="Detalles adicionales del error")


class PaginationParams(BaseModel):
    """Parámetros de paginación"""
    skip: int = Field(0, ge=0, description="Número de registros a omitir")
    limit: int = Field(50, ge=1, le=100, description="Número máximo de registros a retornar")


class LocationParams(BaseModel):
    """Parámetros de ubicación geográfica"""
    lat: float = Field(..., ge=-90, le=90, description="Latitud")
    lon: float = Field(..., ge=-180, le=180, description="Longitud")
    
    class Config:
        json_schema_extra = {
            "example": {
                "lat": -33.4489,
                "lon": -70.6693
            }
        }


class CoordinatesResponse(BaseModel):
    """Respuesta con coordenadas geográficas"""
    latitud: Optional[float] = Field(None, description="Latitud")
    longitud: Optional[float] = Field(None, description="Longitud")


class SupermarketInfo(BaseModel):
    """Información básica de supermercado"""
    id: str = Field(..., description="ID único del supermercado")
    nombre: str = Field(..., description="Nombre del supermercado")
    tipo: str = Field(..., description="Tipo de supermercado (retail/mayorista)")
    logo_url: Optional[str] = Field(None, description="URL del logo")


class CategoryInfo(BaseModel):
    """Información básica de categoría"""
    id: str = Field(..., description="ID único de la categoría")
    nombre: str = Field(..., description="Nombre de la categoría")
    slug: str = Field(..., description="Slug de la categoría")


class PriceInfo(BaseModel):
    """Información de precio"""
    precio_normal: float = Field(..., description="Precio normal del producto")
    precio_descuento: Optional[float] = Field(None, description="Precio con descuento")
    porcentaje_descuento: float = Field(0, description="Porcentaje de descuento")
    precio_efectivo: float = Field(..., description="Precio efectivo (con descuento si aplica)")
    
    @validator('precio_efectivo', always=True)
    def calculate_effective_price(cls, v, values):
        """Calcular precio efectivo automáticamente"""
        if 'precio_descuento' in values and values['precio_descuento']:
            return values['precio_descuento']
        return values.get('precio_normal', 0)


class StoreBasicInfo(BaseModel):
    """Información básica de tienda"""
    id: str = Field(..., description="ID único de la tienda")
    nombre: str = Field(..., description="Nombre de la tienda")
    supermercado: str = Field(..., description="Nombre del supermercado")
    comuna: str = Field(..., description="Comuna donde se ubica")
    direccion: str = Field(..., description="Dirección completa")


class ProductBasicInfo(BaseModel):
    """Información básica de producto"""
    id: str = Field(..., description="ID único del producto")
    nombre: str = Field(..., description="Nombre del producto")
    marca: Optional[str] = Field(None, description="Marca del producto")
    categoria: Optional[str] = Field(None, description="Categoría del producto")


class SearchFilters(BaseModel):
    """Filtros de búsqueda"""
    categoria_id: Optional[UUID] = Field(None, description="ID de categoría para filtrar")
    precio_min: Optional[float] = Field(None, ge=0, description="Precio mínimo")
    precio_max: Optional[float] = Field(None, ge=0, description="Precio máximo")
    radio_km: float = Field(10.0, ge=0.1, le=50, description="Radio de búsqueda en kilómetros")
    incluir_mayoristas: bool = Field(False, description="Incluir supermercados mayoristas")
    
    @validator('precio_max')
    def validate_price_range(cls, v, values):
        """Validar que precio_max sea mayor que precio_min"""
        if v is not None and 'precio_min' in values and values['precio_min'] is not None:
            if v <= values['precio_min']:
                raise ValueError('precio_max debe ser mayor que precio_min')
        return v


class HealthCheckResponse(BaseModel):
    """Respuesta del health check"""
    status: str = Field(..., description="Estado del servicio")
    version: str = Field(..., description="Versión de la API")
    timestamp: datetime = Field(default_factory=datetime.now)
    database: str = Field(..., description="Estado de la base de datos")
    cache: str = Field(..., description="Estado del cache")
    uptime_seconds: float = Field(..., description="Tiempo de actividad en segundos")


class StatisticsResponse(BaseModel):
    """Respuesta con estadísticas"""
    total_tiendas: int = Field(..., description="Total de tiendas encontradas")
    precio_minimo: float = Field(..., description="Precio mínimo encontrado")
    precio_maximo: float = Field(..., description="Precio máximo encontrado")
    precio_promedio: float = Field(..., description="Precio promedio")
    ahorro_maximo: float = Field(..., description="Máximo ahorro posible")
    ofertas_con_descuento: int = Field(..., description="Número de ofertas con descuento")


class RecommendationResponse(BaseModel):
    """Respuesta con recomendación"""
    mejor_precio_tienda: str = Field(..., description="Tienda con mejor precio")
    mejor_precio: float = Field(..., description="Mejor precio encontrado")
    ahorro_vs_mas_caro: float = Field(..., description="Ahorro vs precio más caro")
    tiene_descuento: bool = Field(..., description="Si el mejor precio tiene descuento")
    porcentaje_descuento: float = Field(..., description="Porcentaje de descuento del mejor precio")
    explicacion: str = Field(..., description="Explicación de la recomendación")


# Configuración global para todos los schemas
class Config:
    """Configuración base para schemas"""
    use_enum_values = True
    validate_assignment = True
    populate_by_name = True
    json_encoders = {
        datetime: lambda v: v.isoformat(),
        Decimal: lambda v: float(v),
        UUID: lambda v: str(v)
    }

