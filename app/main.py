"""
Aplicación principal FastAPI para Cuanto Cuesta
"""
import time
import logging
import sys
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi
import uvicorn
import structlog
from structlog.contextvars import bind_contextvars, clear_contextvars

from openai import OpenAIError
from redis.exceptions import RedisError
from sqlalchemy.exc import SQLAlchemyError

from redis import asyncio as aioredis
from fastapi_limiter import FastAPILimiter

from app.core.config import settings
from app.core.database import check_database_connection, create_database
from app.core.cache import cache
from app.api.v1.api import api_router
import routers.gpt_router

# Configurar logging estructurado
log_level_name = "DEBUG" if settings.DEBUG else settings.LOG_LEVEL
log_level = getattr(logging, log_level_name.upper(), logging.INFO)
logging.basicConfig(level=log_level, format="%(message)s", stream=sys.stdout)

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.format_exc_info,
        structlog.dev.ConsoleRenderer() if settings.DEBUG else structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(log_level),
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Variable global para tiempo de inicio
start_time = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):

    logger.info("Iniciando aplicación Cuanto Cuesta...")

    redis = aioredis.from_url(
        settings.REDIS_URL, encoding="utf-8", decode_responses=True
    )
    await FastAPILimiter.init(redis)

    # Verificar conexión a base de datos (desactivado temporalmente)
    # if not await verify_database_connection():
    #     logger.error("No se pudo conectar a la base de datos")
    #     raise Exception("Error de conexión a base de datos")

    yield

    # Shutdown
    await redis.close()
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
    lifespan=lifespan
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware de hosts confiables
if not settings.DEBUG:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS
    )


# Middleware personalizado para logging y métricas
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Middleware para logging de requests con contexto"""
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    user_id = request.headers.get("X-User-ID", "anonymous")
    bind_contextvars(request_id=request_id, user_id=user_id)

    start_time_req = time.time()
    logger.info("Request", method=request.method, url=str(request.url))
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("Error procesando request")
        clear_contextvars()
        raise

    process_time = time.time() - start_time_req
    logger.info(
        "Response",
        status_code=response.status_code,
        process_time=round(process_time, 3),
        path=request.url.path,
    )
    response.headers["X-Process-Time"] = str(process_time)
    clear_contextvars()
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
                "path": str(request.url.path)
            },
            "timestamp": time.time()
        }
    )


@app.exception_handler(OpenAIError)
async def openai_exception_handler(request: Request, exc: OpenAIError):
    """Manejo de errores del cliente de OpenAI"""
    logger.exception("Error en OpenAI")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": 500,
                "message": "Error en servicio OpenAI",
                "path": str(request.url.path),
            },
            "timestamp": time.time(),
        },
    )


@app.exception_handler(RedisError)
async def redis_exception_handler(request: Request, exc: RedisError):
    """Manejo de errores de Redis"""
    logger.exception("Error en Redis")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": 500,
                "message": "Error en servicio Redis",
                "path": str(request.url.path),
            },
            "timestamp": time.time(),
        },
    )


@app.exception_handler(SQLAlchemyError)
async def db_exception_handler(request: Request, exc: SQLAlchemyError):
    """Manejo de errores de base de datos"""
    logger.exception("Error en base de datos")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": 500,
                "message": "Error en base de datos",
                "path": str(request.url.path),
            },
            "timestamp": time.time(),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Manejador de errores generales"""
    logger.exception("Error no manejado")

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


# Endpoint de health check
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint para monitoreo
    """
    # Verificar base de datos
    db_status = "ok" if check_database_connection() else "error"
    
    # Verificar cache
    cache_status = "ok"
    try:
        if cache.redis_client:
            cache.redis_client.ping()
    except:
        cache_status = "error"
    
    # Calcular uptime
    uptime = time.time() - start_time
    
    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "version": settings.PROJECT_VERSION,
        "timestamp": time.time(),
        "database": db_status,
        "cache": cache_status,
        "uptime_seconds": round(uptime, 2),
        "environment": "development" if settings.DEBUG else "production"
    }


# Incluir routers de la API
app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(routers.gpt_router.router)


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
    openapi_schema["info"]["x-logo"] = {
        "url": "https://cuantocuesta.cl/logo.png"
    }
    
    # Agregar información de contacto
    openapi_schema["info"]["contact"] = {
        "name": "Equipo Cuanto Cuesta",
        "email": "api@cuantocuesta.cl",
        "url": "https://cuantocuesta.cl"
    }
    
    # Agregar información de licencia
    openapi_schema["info"]["license"] = {
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT"
    }
    
    # Agregar tags personalizados
    openapi_schema["tags"] = [
        {
            "name": "Productos",
            "description": "Búsqueda y gestión de productos"
        },
        {
            "name": "Precios", 
            "description": "Comparación y análisis de precios"
        },
        {
            "name": "Tiendas",
            "description": "Búsqueda geográfica de tiendas"
        },
        {
            "name": "Health",
            "description": "Monitoreo y estado del sistema"
        }
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
            "API multi-plataforma"
        ]
    }


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )

