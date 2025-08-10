"""
Schemas para tiendas con nomenclatura en español
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, StrictStr
from uuid import UUID

from app.schemas.common import CoordinatesResponse, SupermarketInfo, Config


class StoreSearchRequest(BaseModel):
    """Request para búsqueda de tiendas"""
    termino: StrictStr = Field(
        ..., min_length=1, max_length=100, pattern=r"^[\w\s-]+$", description="Término de búsqueda (comuna, nombre)"
    )
    limite: int = Field(50, ge=1, le=100, description="Número máximo de resultados")
    
    class Config(Config):
        json_schema_extra = {
            "example": {
                "termino": "Ñuñoa",
                "limite": 20
            }
        }


class NearbyStoresRequest(BaseModel):
    """Request para tiendas cercanas"""
    lat: float = Field(..., ge=-90, le=90, description="Latitud")
    lon: float = Field(..., ge=-180, le=180, description="Longitud")
    radio_km: float = Field(10.0, ge=0.1, le=50, description="Radio de búsqueda en kilómetros")
    tipo_supermercado: Optional[str] = Field(None, description="Tipo de supermercado (retail/mayorista)")
    producto_ids: Optional[List[UUID]] = Field(None, description="IDs de productos específicos")
    abierto_ahora: bool = Field(False, description="Solo tiendas abiertas ahora")
    limite: int = Field(50, ge=1, le=100, description="Número máximo de resultados")
    
    class Config(Config):
        json_schema_extra = {
            "example": {
                "lat": -33.4489,
                "lon": -70.6693,
                "radio_km": 10.0,
                "tipo_supermercado": "retail",
                "abierto_ahora": True,
                "limite": 20
            }
        }


class StoreResponse(BaseModel):
    """Respuesta con información de tienda"""
    id: str = Field(..., description="ID único de la tienda")
    nombre: str = Field(..., description="Nombre de la tienda")
    supermercado: str = Field(..., description="Nombre del supermercado")
    tipo_supermercado: str = Field(..., description="Tipo de supermercado")
    direccion: str = Field(..., description="Dirección completa")
    comuna: str = Field(..., description="Comuna")
    region: str = Field(..., description="Región")
    telefono: Optional[str] = Field(None, description="Teléfono de contacto")
    coordenadas: CoordinatesResponse = Field(..., description="Coordenadas geográficas")
    distancia_km: Optional[float] = Field(None, description="Distancia en kilómetros")
    tiempo_estimado: Optional[int] = Field(None, description="Tiempo estimado en minutos")
    horarios: Optional[Dict[str, Any]] = Field(None, description="Horarios de atención")
    abierto_ahora: bool = Field(True, description="Si está abierto actualmente")
    servicios: List[str] = Field(default_factory=list, description="Servicios disponibles")
    logo_supermercado: Optional[str] = Field(None, description="URL del logo del supermercado")
    productos_disponibles: Optional[int] = Field(None, description="Productos disponibles (si aplica)")
    precio_promedio: Optional[float] = Field(None, description="Precio promedio (si aplica)")
    puntuacion_similitud: Optional[float] = Field(None, description="Puntuación de similitud en búsqueda")
    
    class Config(Config):
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "nombre": "Jumbo Ñuñoa",
                "supermercado": "Jumbo",
                "tipo_supermercado": "retail",
                "direccion": "Av. Irarrázaval 4750",
                "comuna": "Ñuñoa",
                "region": "Región Metropolitana",
                "telefono": "+56 2 2345 6789",
                "coordenadas": {
                    "latitud": -33.4489,
                    "longitud": -70.6693
                },
                "distancia_km": 2.5,
                "tiempo_estimado": 8,
                "abierto_ahora": True,
                "servicios": ["farmacia", "panaderia", "estacionamiento"]
            }
        }


class StoreDetailResponse(BaseModel):
    """Respuesta detallada de tienda"""
    id: str = Field(..., description="ID único de la tienda")
    nombre: str = Field(..., description="Nombre de la tienda")
    supermercado: SupermarketInfo = Field(..., description="Información del supermercado")
    direccion: str = Field(..., description="Dirección completa")
    comuna: str = Field(..., description="Comuna")
    region: str = Field(..., description="Región")
    telefono: Optional[str] = Field(None, description="Teléfono")
    email: Optional[str] = Field(None, description="Email de contacto")
    coordenadas: CoordinatesResponse = Field(..., description="Coordenadas geográficas")
    horarios: Optional[Dict[str, Any]] = Field(None, description="Horarios de atención")
    servicios: List[str] = Field(default_factory=list, description="Servicios disponibles")
    tiene_farmacia: bool = Field(False, description="Si tiene farmacia")
    tiene_panaderia: bool = Field(False, description="Si tiene panadería")
    tiene_estacionamiento: bool = Field(False, description="Si tiene estacionamiento")
    nombre_completo: str = Field(..., description="Nombre completo de la tienda")
    
    class Config(Config):
        pass


class StoreSearchResponse(BaseModel):
    """Respuesta de búsqueda de tiendas"""
    tiendas: List[StoreResponse] = Field(..., description="Lista de tiendas encontradas")
    total: int = Field(..., description="Total de tiendas encontradas")
    termino_busqueda: str = Field(..., description="Término de búsqueda utilizado")
    tiempo_respuesta_ms: Optional[int] = Field(None, description="Tiempo de respuesta en milisegundos")
    
    class Config(Config):
        json_schema_extra = {
            "example": {
                "tiendas": [
                    {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "nombre": "Jumbo Ñuñoa",
                        "supermercado": "Jumbo",
                        "comuna": "Ñuñoa",
                        "direccion": "Av. Irarrázaval 4750"
                    }
                ],
                "total": 5,
                "termino_busqueda": "Ñuñoa"
            }
        }


class NearbyStoresResponse(BaseModel):
    """Respuesta de tiendas cercanas"""
    tiendas: List[StoreResponse] = Field(..., description="Lista de tiendas cercanas")
    total: int = Field(..., description="Total de tiendas encontradas")
    ubicacion_busqueda: Dict[str, float] = Field(..., description="Ubicación utilizada para la búsqueda")
    radio_km: float = Field(..., description="Radio de búsqueda utilizado")
    filtros_aplicados: Dict[str, Any] = Field(..., description="Filtros aplicados")
    
    class Config(Config):
        json_schema_extra = {
            "example": {
                "tiendas": [
                    {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "nombre": "Jumbo Ñuñoa",
                        "supermercado": "Jumbo",
                        "distancia_km": 2.5,
                        "tiempo_estimado": 8
                    }
                ],
                "total": 15,
                "ubicacion_busqueda": {"lat": -33.4489, "lon": -70.6693},
                "radio_km": 10.0
            }
        }


class StoreServicesRequest(BaseModel):
    """Request para tiendas con servicios específicos"""
    servicios: List[str] = Field(..., min_items=1, description="Lista de servicios requeridos")
    lat: Optional[float] = Field(None, ge=-90, le=90, description="Latitud")
    lon: Optional[float] = Field(None, ge=-180, le=180, description="Longitud")
    radio_km: float = Field(10.0, ge=0.1, le=50, description="Radio de búsqueda")
    limite: int = Field(50, ge=1, le=100, description="Número máximo de resultados")
    
    class Config(Config):
        json_schema_extra = {
            "example": {
                "servicios": ["farmacia", "panaderia"],
                "lat": -33.4489,
                "lon": -70.6693,
                "radio_km": 5.0,
                "limite": 20
            }
        }


class StoreServicesResponse(BaseModel):
    """Respuesta de tiendas con servicios"""
    tiendas: List[StoreResponse] = Field(..., description="Lista de tiendas con servicios")
    servicios_solicitados: List[str] = Field(..., description="Servicios solicitados")
    total: int = Field(..., description="Total de tiendas encontradas")
    ubicacion: Optional[Dict[str, float]] = Field(None, description="Ubicación utilizada")
    
    class Config(Config):
        pass


class SupermarketResponse(BaseModel):
    """Respuesta con información de supermercado"""
    id: str = Field(..., description="ID único del supermercado")
    nombre: str = Field(..., description="Nombre del supermercado")
    slug: str = Field(..., description="Slug del supermercado")
    tipo: str = Field(..., description="Tipo (retail/mayorista)")
    logo_url: Optional[str] = Field(None, description="URL del logo")
    sitio_web: Optional[str] = Field(None, description="Sitio web")
    compra_minima: Optional[float] = Field(None, description="Monto mínimo de compra")
    delivery_disponible: bool = Field(False, description="Si tiene delivery")
    pickup_disponible: bool = Field(True, description="Si tiene pickup")
    total_tiendas: int = Field(0, description="Total de tiendas")
    
    class Config(Config):
        pass


class SupermarketsListResponse(BaseModel):
    """Respuesta con lista de supermercados"""
    supermercados: List[SupermarketResponse] = Field(..., description="Lista de supermercados")
    total: int = Field(..., description="Total de supermercados")
    
    class Config(Config):
        pass

