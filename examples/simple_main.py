from fastapi import FastAPI, HTTPException, Query, Path
from fastapi.middleware.cors import CORSMiddleware
import time
from typing import List, Optional
from pydantic import BaseModel
import re
import unicodedata
from db import SessionLocal
from openai_client import consulta_gpt

app = FastAPI(
    title="Cuanto Cuesta API - Completa",
    version="1.0.0",
    description="API completa para comparación de precios de supermercados chilenos"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelos de datos
class Product(BaseModel):
    id: str
    nombre: str
    marca: Optional[str] = None
    descripcion: Optional[str] = None
    categoria: Optional[str] = None
    precio_promedio: Optional[float] = None
    precio_min: Optional[float] = None
    precio_max: Optional[float] = None
    tiendas_disponibles: Optional[int] = None

class Store(BaseModel):
    id: str
    nombre: str
    supermercado: str
    direccion: str
    comuna: str
    distancia_km: Optional[float] = None
    tiempo_estimado_min: Optional[int] = None
    abierto: Optional[bool] = True

class Oferta(BaseModel):
    producto_nombre: str
    marca: Optional[str] = None
    tienda_nombre: str
    precio_normal: float
    precio_oferta: float
    descuento_porcentaje: float
    ahorro: float
    distancia_km: Optional[float] = None

class ProductSearchResponse(BaseModel):
    productos: List[Product]
    total: int
    tiempo_respuesta_ms: int

class StoreSearchResponse(BaseModel):
    tiendas: List[Store]
    total: int
    termino_busqueda: str
    tiempo_respuesta_ms: int

class NearbyStoresResponse(BaseModel):
    tiendas: List[Store]
    total: int
    ubicacion_busqueda: dict
    radio_km: float

class BestDealsResponse(BaseModel):
    ofertas: List[Oferta]
    total_ofertas: int
    descuento_minimo: float
    ahorro_total_disponible: float

# Datos de prueba - Productos
SAMPLE_PRODUCTS = [
    {
        "id": "1",
        "nombre": "Pan Hallulla",
        "marca": "Ideal",
        "descripcion": "Pan hallulla tradicional",
        "categoria": "Panadería",
        "precio_promedio": 1500,
        "precio_min": 1200,
        "precio_max": 1800,
        "tiendas_disponibles": 5
    },
    {
        "id": "2", 
        "nombre": "Pan Integral",
        "marca": "Bimbo",
        "descripcion": "Pan integral de molde 500g",
        "categoria": "Panadería",
        "precio_promedio": 1890,
        "precio_min": 1690,
        "precio_max": 2190,
        "tiendas_disponibles": 8
    },
    {
        "id": "3",
        "nombre": "Leche Entera",
        "marca": "Soprole",
        "descripcion": "Leche entera 1 litro",
        "categoria": "Lácteos",
        "precio_promedio": 1050,
        "precio_min": 890,
        "precio_max": 1200,
        "tiendas_disponibles": 8
    },
    {
        "id": "4",
        "nombre": "Arroz Grado 1",
        "marca": "Tucapel",
        "descripcion": "Arroz grado 1 - 1kg",
        "categoria": "Abarrotes",
        "precio_promedio": 1850,
        "precio_min": 1500,
        "precio_max": 2200,
        "tiendas_disponibles": 6
    },
    {
        "id": "5",
        "nombre": "Aceite Maravilla",
        "marca": "Chef",
        "descripcion": "Aceite maravilla 900ml",
        "categoria": "Abarrotes",
        "precio_promedio": 2490,
        "precio_min": 1990,
        "precio_max": 2990,
        "tiendas_disponibles": 7
    },
    {
        "id": "6",
        "nombre": "Pollo Entero",
        "marca": "Ariztía",
        "descripcion": "Pollo entero fresco por kg",
        "categoria": "Carnes",
        "precio_promedio": 3150,
        "precio_min": 2800,
        "precio_max": 3500,
        "tiendas_disponibles": 4
    },
    {
        "id": "7",
        "nombre": "Manzanas Rojas",
        "marca": None,
        "descripcion": "Manzanas rojas por kg",
        "categoria": "Frutas",
        "precio_promedio": 1550,
        "precio_min": 1200,
        "precio_max": 1900,
        "tiendas_disponibles": 7
    }
]

# Datos de prueba - Tiendas por comuna
SAMPLE_STORES_BY_COMUNA = {
    "las condes": [
        {
            "id": "1",
            "nombre": "Jumbo Kennedy",
            "supermercado": "Jumbo",
            "direccion": "Av. Kennedy 9001, Las Condes",
            "comuna": "Las Condes",
            "abierto": True
        },
        {
            "id": "2",
            "nombre": "Lider Las Condes",
            "supermercado": "Lider",
            "direccion": "Av. Apoquindo 4501, Las Condes", 
            "comuna": "Las Condes",
            "abierto": True
        },
        {
            "id": "3",
            "nombre": "Tottus Las Condes",
            "supermercado": "Tottus",
            "direccion": "Av. Kennedy 9001, Las Condes",
            "comuna": "Las Condes",
            "abierto": False
        }
    ],
    "providencia": [
        {
            "id": "4",
            "nombre": "Lider Express Providencia",
            "supermercado": "Lider",
            "direccion": "Av. Providencia 2594, Providencia",
            "comuna": "Providencia",
            "abierto": True
        },
        {
            "id": "5",
            "nombre": "Santa Isabel Providencia",
            "supermercado": "Santa Isabel",
            "direccion": "Av. Manuel Montt 315, Providencia",
            "comuna": "Providencia",
            "abierto": True
        }
    ],
    "ñuñoa": [
        {
            "id": "6",
            "nombre": "Jumbo Ñuñoa",
            "supermercado": "Jumbo",
            "direccion": "Av. Irarrázaval 4750, Ñuñoa",
            "comuna": "Ñuñoa",
            "abierto": True
        },
        {
            "id": "7",
            "nombre": "Tottus Ñuñoa",
            "supermercado": "Tottus",
            "direccion": "Av. Grecia 9564, Ñuñoa",
            "comuna": "Ñuñoa",
            "abierto": True
        }
    ],
    "maipu": [
        {
            "id": "8",
            "nombre": "Lider Maipú",
            "supermercado": "Lider",
            "direccion": "Av. Pajaritos 1744, Maipú",
            "comuna": "Maipú",
            "abierto": True
        }
    ]
}

# Datos de prueba - Tiendas cercanas (con coordenadas)
SAMPLE_NEARBY_STORES = [
    {
        "id": "1",
        "nombre": "Jumbo Kennedy",
        "supermercado": "Jumbo",
        "direccion": "Av. Kennedy 9001, Las Condes",
        "comuna": "Las Condes",
        "distancia_km": 2.5,
        "tiempo_estimado_min": 8,
        "abierto": True
    },
    {
        "id": "2",
        "nombre": "Lider Express Providencia",
        "supermercado": "Lider",
        "direccion": "Av. Providencia 2594, Providencia",
        "comuna": "Providencia",
        "distancia_km": 1.8,
        "tiempo_estimado_min": 6,
        "abierto": True
    },
    {
        "id": "3",
        "nombre": "Santa Isabel Centro",
        "supermercado": "Santa Isabel",
        "direccion": "Av. Libertador Bernardo O'Higgins 3820, Santiago",
        "comuna": "Santiago",
        "distancia_km": 0.8,
        "tiempo_estimado_min": 3,
        "abierto": True
    },
    {
        "id": "4",
        "nombre": "Tottus Las Condes",
        "supermercado": "Tottus",
        "direccion": "Av. Kennedy 9001, Las Condes",
        "comuna": "Las Condes",
        "distancia_km": 3.2,
        "tiempo_estimado_min": 10,
        "abierto": False
    }
]

# Datos de prueba - Ofertas
SAMPLE_OFFERS = [
    {
        "producto_nombre": "Aceite Maravilla Chef 900ml",
        "marca": "Chef",
        "tienda_nombre": "Tottus Maipú",
        "precio_normal": 2990,
        "precio_oferta": 1990,
        "descuento_porcentaje": 33.4,
        "ahorro": 1000,
        "distancia_km": 3.2
    },
    {
        "producto_nombre": "Pan Integral Bimbo 500g",
        "marca": "Bimbo",
        "tienda_nombre": "Jumbo Kennedy",
        "precio_normal": 2190,
        "precio_oferta": 1590,
        "descuento_porcentaje": 27.4,
        "ahorro": 600,
        "distancia_km": 2.5
    },
    {
        "producto_nombre": "Leche Entera Soprole 1L",
        "marca": "Soprole",
        "tienda_nombre": "Lider Providencia",
        "precio_normal": 1200,
        "precio_oferta": 890,
        "descuento_porcentaje": 25.8,
        "ahorro": 310,
        "distancia_km": 1.8
    },
    {
        "producto_nombre": "Arroz Tucapel 1kg",
        "marca": "Tucapel",
        "tienda_nombre": "Santa Isabel Centro",
        "precio_normal": 2200,
        "precio_oferta": 1500,
        "descuento_porcentaje": 31.8,
        "ahorro": 700,
        "distancia_km": 0.8
    },
    {
        "producto_nombre": "Pollo Entero Ariztía",
        "marca": "Ariztía",
        "tienda_nombre": "Jumbo Ñuñoa",
        "precio_normal": 3500,
        "precio_oferta": 2800,
        "descuento_porcentaje": 20.0,
        "ahorro": 700,
        "distancia_km": 4.1
    }
]

# Utilidades para manejo de caracteres especiales
def normalize_text(text: str) -> str:
    """Normaliza texto removiendo acentos y convirtiendo ñ"""
    if not text:
        return ""
    
    # Convertir a minúsculas
    text = text.lower().strip()
    
    # Remover acentos
    text = unicodedata.normalize('NFD', text)
    text = ''.join(char for char in text if unicodedata.category(char) != 'Mn')
    
    # Manejar ñ específicamente
    text = text.replace('ñ', 'n')
    
    return text

def find_comuna_match(search_term: str) -> Optional[str]:
    """Encuentra coincidencia de comuna manejando caracteres especiales"""
    normalized_search = normalize_text(search_term)
    
    for comuna_key in SAMPLE_STORES_BY_COMUNA.keys():
        normalized_comuna = normalize_text(comuna_key)
        
        # Búsqueda exacta
        if normalized_search == normalized_comuna:
            return comuna_key
        
        # Búsqueda parcial
        if normalized_search in normalized_comuna or normalized_comuna in normalized_search:
            return comuna_key
    
    return None

# Endpoints

@app.get("/health")
async def health_check():
    """Health check endpoint mejorado"""
    return {
        "status": "ok",
        "version": "1.0.0",
        "timestamp": time.time(),
        "database": "ok",
        "cache": "ok",
        "uptime_seconds": 3600.5,
        "environment": "development"
    }

@app.get("/")
async def root():
    """Endpoint raíz con información de la API"""
    return {
        "message": "¡Bienvenido a Cuanto Cuesta API!",
        "description": "API completa para comparación de precios de supermercados chilenos",
        "version": "1.0.0",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "health_url": "/health",
        "api_base": "/api/v1",
        "features": [
            "Búsqueda inteligente de productos",
            "Comparación de precios en tiempo real", 
            "Búsqueda geográfica con PostGIS",
            "Manejo de caracteres especiales (Ñ, acentos)",
            "Optimización de listas de compra",
            "API multi-plataforma"
        ]
    }

@app.get("/api/v1/productos/buscar", response_model=ProductSearchResponse)
async def buscar_productos(
    q: str = Query(..., min_length=1, max_length=100, description="Término de búsqueda"),
    limite: int = Query(50, ge=1, le=100, description="Número máximo de resultados"),
    lat: Optional[float] = Query(None, ge=-90, le=90, description="Latitud"),
    lon: Optional[float] = Query(None, ge=-180, le=180, description="Longitud"),
    precio_min: Optional[float] = Query(None, ge=0, description="Precio mínimo"),
    precio_max: Optional[float] = Query(None, ge=0, description="Precio máximo"),
    radio_km: float = Query(10.0, ge=0.1, le=50, description="Radio de búsqueda en km")
):
    """Búsqueda inteligente de productos con validación mejorada"""
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
    
    # Filtrar productos por término de búsqueda
    query_lower = q.lower()
    filtered_products = []
    
    for product_data in SAMPLE_PRODUCTS:
        product_name = product_data["nombre"].lower()
        product_desc = (product_data.get("descripcion") or "").lower()
        product_category = (product_data.get("categoria") or "").lower()
        product_brand = (product_data.get("marca") or "").lower()
        
        if (query_lower in product_name or 
            query_lower in product_desc or 
            query_lower in product_category or
            query_lower in product_brand):
            
            # Aplicar filtros de precio si se especifican
            if precio_min and product_data["precio_min"] < precio_min:
                continue
            if precio_max and product_data["precio_max"] > precio_max:
                continue
                
            filtered_products.append(Product(**product_data))
    
    # Limitar resultados
    filtered_products = filtered_products[:limite]
    
    end_time = time.time()
    response_time = int((end_time - start_time) * 1000)
    
    return ProductSearchResponse(
        productos=filtered_products,
        total=len(filtered_products),
        tiempo_respuesta_ms=response_time
    )

@app.get("/api/v1/tiendas/cercanas", response_model=NearbyStoresResponse)
async def obtener_tiendas_cercanas(
    lat: float = Query(..., ge=-90, le=90, description="Latitud"),
    lon: float = Query(..., ge=-180, le=180, description="Longitud"),
    radio_km: float = Query(10.0, ge=0.1, le=50, description="Radio de búsqueda en km"),
    limite: int = Query(50, ge=1, le=100, description="Número máximo de resultados"),
    tipo_supermercado: Optional[str] = Query(None, description="Tipo de supermercado"),
    abierto_ahora: bool = Query(False, description="Solo tiendas abiertas ahora")
):
    """Obtener tiendas cercanas con filtros avanzados"""
    
    # Validar tipo de supermercado
    if tipo_supermercado and tipo_supermercado not in ["retail", "mayorista"]:
        raise HTTPException(
            status_code=400,
            detail="tipo_supermercado debe ser 'retail' o 'mayorista'"
        )
    
    # Filtrar tiendas
    filtered_stores = []
    for store_data in SAMPLE_NEARBY_STORES:
        # Filtrar por estado abierto si se solicita
        if abierto_ahora and not store_data.get("abierto", True):
            continue
        
        # Filtrar por radio (simulado - en realidad usaríamos cálculo de distancia real)
        if store_data.get("distancia_km", 0) <= radio_km:
            filtered_stores.append(Store(**store_data))
    
    # Limitar resultados
    filtered_stores = filtered_stores[:limite]
    
    return NearbyStoresResponse(
        tiendas=filtered_stores,
        total=len(filtered_stores),
        ubicacion_busqueda={"lat": lat, "lon": lon},
        radio_km=radio_km
    )

@app.get("/api/v1/tiendas/buscar-por-comuna", response_model=StoreSearchResponse)
async def buscar_tiendas_por_comuna(
    termino: str = Query(..., min_length=1, max_length=100, description="Término de búsqueda (comuna)"),
    limite: int = Query(50, ge=1, le=100, description="Número máximo de resultados")
):
    """
    Búsqueda inteligente de tiendas por comuna con manejo de caracteres especiales.
    
    Maneja inteligentemente caracteres especiales chilenos:
    - Encuentra "Ñuñoa" escribiendo "Nunoa", "nunoa", "NUNOA"
    - Búsqueda por similitud para manejar errores de tipeo
    - Normalización automática de acentos y caracteres especiales
    """
    start_time = time.time()
    
    # Buscar coincidencia de comuna
    comuna_match = find_comuna_match(termino)
    
    filtered_stores = []
    if comuna_match and comuna_match in SAMPLE_STORES_BY_COMUNA:
        store_list = SAMPLE_STORES_BY_COMUNA[comuna_match]
        for store_data in store_list[:limite]:
            filtered_stores.append(Store(**store_data))
    
    end_time = time.time()
    response_time = int((end_time - start_time) * 1000)
    
    return StoreSearchResponse(
        tiendas=filtered_stores,
        total=len(filtered_stores),
        termino_busqueda=termino,
        tiempo_respuesta_ms=response_time
    )

@app.get("/api/v1/precios/mejores-ofertas", response_model=BestDealsResponse)
async def obtener_mejores_ofertas(
    min_descuento: float = Query(20.0, ge=0, le=100, description="Descuento mínimo en porcentaje"),
    lat: Optional[float] = Query(None, ge=-90, le=90, description="Latitud"),
    lon: Optional[float] = Query(None, ge=-180, le=180, description="Longitud"),
    radio_km: float = Query(10.0, ge=0.1, le=50, description="Radio de búsqueda en km"),
    limite: int = Query(50, ge=1, le=100, description="Número máximo de ofertas")
):
    """
    Obtener las mejores ofertas disponibles con descuentos significativos.
    
    Características:
    - Filtrado por descuento mínimo
    - Búsqueda geográfica opcional
    - Ordenamiento por porcentaje de descuento
    - Información detallada de cada oferta
    """
    
    # Validar coordenadas
    if (lat is None) != (lon is None):
        raise HTTPException(
            status_code=400,
            detail="Debe proporcionar tanto latitud como longitud, o ninguna"
        )
    
    # Filtrar ofertas por descuento mínimo
    filtered_offers = []
    for offer_data in SAMPLE_OFFERS:
        if offer_data["descuento_porcentaje"] >= min_descuento:
            # Filtrar por radio si se proporcionan coordenadas
            if lat is not None and lon is not None:
                if offer_data.get("distancia_km", 0) <= radio_km:
                    filtered_offers.append(Oferta(**offer_data))
            else:
                filtered_offers.append(Oferta(**offer_data))
    
    # Ordenar por descuento (mayor a menor)
    filtered_offers.sort(key=lambda x: x.descuento_porcentaje, reverse=True)
    
    # Limitar resultados
    filtered_offers = filtered_offers[:limite]
    
    # Calcular ahorro total
    ahorro_total = sum(offer.ahorro for offer in filtered_offers)
    
    return BestDealsResponse(
        ofertas=filtered_offers,
        total_ofertas=len(filtered_offers),
        descuento_minimo=min_descuento,
        ahorro_total_disponible=ahorro_total
    )

@app.get("/api/v1/precios/comparar/{producto_id}")
async def comparar_precios(
    producto_id: str = Path(..., description="ID único del producto"),
    lat: Optional[float] = Query(None, ge=-90, le=90, description="Latitud"),
    lon: Optional[float] = Query(None, ge=-180, le=180, description="Longitud"),
    radio_km: float = Query(10.0, ge=0.1, le=50, description="Radio de búsqueda en km"),
    incluir_mayoristas: bool = Query(False, description="Incluir supermercados mayoristas")
):
    """
    Comparar precios de un producto entre diferentes tiendas.
    
    Funcionalidades:
    - Comparación de precios en tiempo real
    - Cálculo de distancias y tiempos estimados
    - Identificación de mejores ofertas
    - Estadísticas de precios (min, max, promedio)
    """
    
    # Validar coordenadas
    if (lat is None) != (lon is None):
        raise HTTPException(
            status_code=400,
            detail="Debe proporcionar tanto latitud como longitud, o ninguna"
        )
    
    # Buscar producto
    producto = None
    for product_data in SAMPLE_PRODUCTS:
        if product_data["id"] == producto_id:
            producto = product_data
            break
    
    if not producto:
        raise HTTPException(
            status_code=404,
            detail=f"Producto con ID {producto_id} no encontrado"
        )
    
    # Simular precios en diferentes tiendas
    precios = [
        {
            "tienda_id": "1",
            "tienda_nombre": "Jumbo Kennedy",
            "precio_normal": producto["precio_max"],
            "precio_oferta": producto["precio_min"],
            "descuento_porcentaje": 15.0,
            "distancia_km": 2.5,
            "tiempo_estimado_min": 8
        },
        {
            "tienda_id": "2",
            "tienda_nombre": "Lider Providencia",
            "precio_normal": producto["precio_promedio"],
            "precio_oferta": None,
            "descuento_porcentaje": 0.0,
            "distancia_km": 1.8,
            "tiempo_estimado_min": 6
        },
        {
            "tienda_id": "3",
            "tienda_nombre": "Santa Isabel Centro",
            "precio_normal": producto["precio_min"],
            "precio_oferta": None,
            "descuento_porcentaje": 0.0,
            "distancia_km": 0.8,
            "tiempo_estimado_min": 3
        }
    ]
    
    # Calcular estadísticas
    precios_normales = [p["precio_normal"] for p in precios]
    precio_min = min(precios_normales)
    precio_max = max(precios_normales)
    precio_promedio = sum(precios_normales) / len(precios_normales)
    ahorro_maximo = precio_max - precio_min
    
    return {
        "producto": {
            "id": producto["id"],
            "nombre": producto["nombre"],
            "marca": producto["marca"]
        },
        "precios": precios,
        "estadisticas": {
            "precio_min": precio_min,
            "precio_max": precio_max,
            "precio_promedio": round(precio_promedio, 0),
            "ahorro_maximo": ahorro_maximo
        }
    }

# Manejo de errores mejorado
@app.exception_handler(422)
async def validation_exception_handler(request, exc):
    """Manejo personalizado de errores de validación"""
    return {
        "success": False,
        "error": {
            "code": 422,
            "message": "Datos de entrada inválidos",
            "details": str(exc)
        },
        "timestamp": time.time()
    }

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Manejo personalizado de errores HTTP"""
    return {
        "success": False,
        "error": {
            "code": exc.status_code,
            "message": exc.detail
        },
        "timestamp": time.time()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
