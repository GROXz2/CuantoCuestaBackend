"""
Aplicación principal FastAPI para Cuanto Cuesta
"""
import logging
import time
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from app.api.v1.api import api_router
from app.api.v1.routers.health import router as health_router
from app.core.config import settings

try:
    from prometheus_fastapi_instrumentator import Instrumentator
except Exception:  # pragma: no cover - opcional si no está instalado
    Instrumentator = None

# Configurar logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Iniciando aplicación Cuanto Cuesta...")

    # Verificar conexión a base de datos (desactivado temporalmente)
    # if not await verify_database_connection():
    #     logger.error("No se pudo conectar a la base de datos")
    #     raise Exception("Error de conexión a base de datos")

    yield

    # Shutdown
    logger.info("Cerrando aplicación...")


# Crear aplicación FastAPI
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="""
    API REST para comparación de precios de supermercados chilenos.
    
    ## Características principales
    
    * **Búsqueda inteligente** de productos con manejo de caracteres especiales
    * **Comparación de precios** en tiempo real entre diferentes tiendas
    * **Búsqueda geográfica** con cálculo preciso de distancias
    * **Manejo especial de caracteres chilenos** (ej: Ñuñoa, Peñalolén)
    * **Optimización de listas de compra** con algoritmos de ahorro
    * **API multi-plataforma** optimizada para GPT, Chrome Extension y App Móvil
    
    ## Funcionalidades especiales
    
    ### Manejo de caracteres especiales
    La API maneja inteligentemente caracteres especiales chilenos:
    - Buscar "Ñuñoa" funciona escribiendo "Nunoa", "nunoa", "NUNOA"
    - Buscar "Peñalolén" funciona escribiendo "Penalolen"
    - Normalización automática de acentos y tildes
    
    ### Búsqueda geográfica
    - Cálculo preciso de distancias usando PostGIS
    - Estimación de tiempos de viaje
    - Filtrado por radio de búsqueda
    - Ordenamiento por distancia o precio
    
    ### Optimización de compras
    - Algoritmos de optimización precio vs distancia
    - Sugerencias de rutas de compra
    - Análisis de ahorro por tienda
    - Recomendaciones inteligentes
    
    ## Endpoints principales
    
    * `/productos/buscar` - Búsqueda inteligente de productos
    * `/precios/comparar/{producto_id}` - Comparación de precios
    * `/tiendas/cercanas` - Tiendas cercanas con geolocalización
    * `/tiendas/buscar-por-comuna` - Búsqueda por comuna con manejo de Ñ
    
    ## Autenticación
    
    Algunos endpoints requieren autenticación JWT (funcionalidad futura).
    """,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar dominios exactos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware de hosts confiables
if not settings.DEBUG:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)


# Middleware personalizado para logging y métricas
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Middleware para logging de requests"""
    start_time_req = time.time()

    # Log del request
    logger.info(f"Request: {request.method} {request.url}")

    # Procesar request
    response = await call_next(request)

    # Calcular tiempo de procesamiento
    process_time = time.time() - start_time_req

    # Log de la respuesta
    logger.info(
        f"Response: {response.status_code} - "
        f"Time: {process_time:.3f}s - "
        f"Path: {request.url.path}"
    )

    # Agregar header con tiempo de procesamiento
    response.headers["X-Process-Time"] = str(process_time)

    return response


# Manejador de errores global
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Manejador personalizado de errores HTTP"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.status_code,
                "message": exc.detail,
                "path": str(request.url.path),
            },
            "timestamp": time.time(),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Manejador de errores generales"""
    logger.error(f"Error no manejado: {exc}", exc_info=True)

    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": 500,
                "message": "Error interno del servidor",
                "path": str(request.url.path),
            },
            "timestamp": time.time(),
        },
    )


# Incluir routers
app.include_router(health_router)
app.include_router(api_router, prefix=settings.API_V1_STR)

# Exponer métricas para Prometheus
if Instrumentator:
    Instrumentator().instrument(app).expose(app)


# Personalizar OpenAPI schema
def custom_openapi():
    """Personalizar documentación OpenAPI"""
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=settings.PROJECT_NAME,
        version=settings.PROJECT_VERSION,
        description=app.description,
        routes=app.routes,
    )

    base_url = settings.BASE_URL or "https://cuantocuestabackend.onrender.com"
    openapi_schema["servers"] = [{"url": base_url}]

    # Personalizar información adicional
    openapi_schema["info"]["x-logo"] = {"url": "https://cuantocuesta.cl/logo.png"}

    # Agregar información de contacto
    openapi_schema["info"]["contact"] = {
        "name": "Equipo Cuanto Cuesta",
        "email": "api@cuantocuesta.cl",
        "url": "https://cuantocuesta.cl",
    }

    # Agregar información de licencia
    openapi_schema["info"]["license"] = {
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    }

    # Agregar tags personalizados
    openapi_schema["tags"] = [
        {"name": "Productos", "description": "Búsqueda y gestión de productos"},
        {"name": "Precios", "description": "Comparación y análisis de precios"},
        {"name": "Tiendas", "description": "Búsqueda geográfica de tiendas"},
        {"name": "Health", "description": "Monitoreo y estado del sistema"},
    ]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


# Endpoint raíz
@app.get("/", tags=["Root"])
async def root():
    """
    Endpoint raíz con información de la API
    """
    return {
        "message": "¡Bienvenido a Cuanto Cuesta API!",
        "description": "API para comparación de precios de supermercados chilenos",
        "version": settings.PROJECT_VERSION,
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "health_url": "/health",
        "api_base": settings.API_V1_STR,
        "features": [
            "Búsqueda inteligente de productos",
            "Comparación de precios en tiempo real",
            "Búsqueda geográfica con PostGIS",
            "Manejo de caracteres especiales (Ñ, acentos)",
            "Optimización de listas de compra",
            "API multi-plataforma",
        ],
    }


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
