"""
Schemas para productos con nomenclatura en español
"""
from typing import Optional, List
from pydantic import BaseModel, Field, StrictStr
from uuid import UUID

from app.schemas.common import CategoryInfo, PriceInfo, Config


class ProductSearchRequest(BaseModel):
    """Request para búsqueda de productos"""
    q: StrictStr = Field(
        ..., min_length=1, max_length=100, pattern=r"^[\w\s-]+$", description="Término de búsqueda"
    )
    categoria_id: Optional[UUID] = Field(None, description="ID de categoría para filtrar")
    precio_min: Optional[float] = Field(None, ge=0, description="Precio mínimo")
    precio_max: Optional[float] = Field(None, ge=0, description="Precio máximo")
    lat: Optional[float] = Field(None, ge=-90, le=90, description="Latitud para búsqueda geográfica")
    lon: Optional[float] = Field(None, ge=-180, le=180, description="Longitud para búsqueda geográfica")
    radio_km: float = Field(10.0, ge=0.1, le=50, description="Radio de búsqueda en kilómetros")
    limite: int = Field(50, ge=1, le=100, description="Número máximo de resultados")
    skip: int = Field(0, ge=0, description="Número de resultados a omitir")
    
    class Config(Config):
        json_schema_extra = {
            "example": {
                "q": "pan integral",
                "categoria_id": None,
                "precio_min": 500,
                "precio_max": 2000,
                "lat": -33.4489,
                "lon": -70.6693,
                "radio_km": 10.0,
                "limite": 20
            }
        }


class ProductResponse(BaseModel):
    """Respuesta con información de producto"""
    id: str = Field(..., description="ID único del producto")
    nombre: str = Field(..., description="Nombre del producto")
    marca: Optional[str] = Field(None, description="Marca del producto")
    categoria: Optional[str] = Field(None, description="Nombre de la categoría")
    codigo_barras: Optional[str] = Field(None, description="Código de barras")
    tipo_unidad: str = Field(..., description="Tipo de unidad (unidad, kg, litro)")
    tamaño_unidad: Optional[str] = Field(None, description="Tamaño de la unidad (500g, 1L)")
    imagen_url: Optional[str] = Field(None, description="URL de la imagen del producto")
    descripcion: Optional[str] = Field(None, description="Descripción del producto")
    nombre_completo: str = Field(..., description="Nombre completo con marca")
    
    # Información de precios (si está disponible)
    precio_mejor: Optional[float] = Field(None, description="Mejor precio encontrado")
    precio_normal: Optional[float] = Field(None, description="Precio normal promedio")
    tiene_descuento: Optional[bool] = Field(None, description="Si tiene descuento disponible")
    porcentaje_descuento: Optional[float] = Field(None, description="Porcentaje de descuento")
    tienda_mejor_precio: Optional[str] = Field(None, description="Tienda con mejor precio")
    tiendas_disponibles: int = Field(0, description="Número de tiendas donde está disponible")
    marca_sugerida: Optional[str] = Field(
        None, description="Marca alternativa sugerida cuando no hay stock"
    )
    explicacion: Optional[str] = Field(
        None, description="Explicación de la sugerencia de marca"
    )
    
    class Config(Config):
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "nombre": "Pan Integral",
                "marca": "Bimbo",
                "categoria": "Panadería",
                "codigo_barras": "7802900123456",
                "tipo_unidad": "unidad",
                "tamaño_unidad": "500g",
                "nombre_completo": "Bimbo Pan Integral",
                "precio_mejor": 990,
                "precio_normal": 1250,
                "tiene_descuento": True,
                "porcentaje_descuento": 20.8,
                "tienda_mejor_precio": "Jumbo Ñuñoa",
                "tiendas_disponibles": 5
            }
        }


class ProductDetailResponse(BaseModel):
    """Respuesta detallada de producto"""
    id: str = Field(..., description="ID único del producto")
    nombre: str = Field(..., description="Nombre del producto")
    marca: Optional[str] = Field(None, description="Marca del producto")
    categoria: Optional[CategoryInfo] = Field(None, description="Información de la categoría")
    codigo_barras: Optional[str] = Field(None, description="Código de barras")
    descripcion: Optional[str] = Field(None, description="Descripción del producto")
    tipo_unidad: str = Field(..., description="Tipo de unidad")
    tamaño_unidad: Optional[str] = Field(None, description="Tamaño de la unidad")
    imagen_url: Optional[str] = Field(None, description="URL de la imagen")
    nombre_completo: str = Field(..., description="Nombre completo con marca")
    unidad_display: str = Field(..., description="Unidad formateada para mostrar")
    
    class Config(Config):
        pass


class ProductSearchResponse(BaseModel):
    """Respuesta de búsqueda de productos"""
    productos: List[ProductResponse] = Field(..., description="Lista de productos encontrados")
    total: int = Field(..., description="Total de productos encontrados")
    termino_busqueda: str = Field(..., description="Término de búsqueda utilizado")
    filtros_aplicados: dict = Field(..., description="Filtros aplicados en la búsqueda")
    tiempo_respuesta_ms: Optional[int] = Field(None, description="Tiempo de respuesta en milisegundos")
    
    class Config(Config):
        json_schema_extra = {
            "example": {
                "productos": [
                    {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "nombre": "Pan Integral",
                        "marca": "Bimbo",
                        "categoria": "Panadería",
                        "precio_mejor": 990,
                        "precio_promedio": 1250,
                        "tiendas_disponibles": 5
                    }
                ],
                "total": 25,
                "termino_busqueda": "pan integral",
                "tiempo_respuesta_ms": 150
            }
        }


class PopularProductsResponse(BaseModel):
    """Respuesta de productos populares"""
    productos: List[ProductResponse] = Field(..., description="Lista de productos populares")
    criterio: str = Field("popularidad", description="Criterio de ordenamiento")
    limite: int = Field(..., description="Límite de productos retornados")
    
    class Config(Config):
        pass


class ProductDiscountsResponse(BaseModel):
    """Respuesta de productos con descuentos"""
    productos: List[ProductResponse] = Field(..., description="Lista de productos con descuentos")
    descuento_minimo: float = Field(..., description="Descuento mínimo aplicado como filtro")
    ubicacion: Optional[dict] = Field(None, description="Ubicación utilizada para filtrar")
    total_ofertas: int = Field(..., description="Total de ofertas encontradas")
    
    class Config(Config):
        pass


class ProductBarcodeRequest(BaseModel):
    """Request para búsqueda por código de barras"""
    codigo_barras: StrictStr = Field(
        ..., min_length=8, max_length=20, pattern=r"^[0-9]+$", description="Código de barras del producto"
    )
    
    class Config(Config):
        json_schema_extra = {
            "example": {
                "codigo_barras": "7802900123456"
            }
        }


class CategoryResponse(BaseModel):
    """Respuesta con información de categoría"""
    id: str = Field(..., description="ID único de la categoría")
    nombre: str = Field(..., description="Nombre de la categoría")
    slug: str = Field(..., description="Slug de la categoría")
    descripcion: Optional[str] = Field(None, description="Descripción de la categoría")
    categoria_padre: Optional[str] = Field(None, description="Categoría padre si existe")
    icono_url: Optional[str] = Field(None, description="URL del icono")
    total_productos: int = Field(0, description="Total de productos en esta categoría")
    
    class Config(Config):
        pass


class CategoriesListResponse(BaseModel):
    """Respuesta con lista de categorías"""
    categorias: List[CategoryResponse] = Field(..., description="Lista de categorías")
    total: int = Field(..., description="Total de categorías")
    
    class Config(Config):
        pass

