"""Aplicación principal FastAPI para Cuanto Cuesta"""
import logging
import sys
import uuid
import time
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi

import structlog
from structlog.contextvars import bind_contextvars, clear_contextvars

from openai import OpenAIError
from redis.exceptions import RedisError
from sqlalchemy.exc import SQLAlchemyError

from redis import asyncio as aioredis

try:
    from fastapi_limiter import FastAPILimiter
except ImportError:
    FastAPILimiter = None

from app.core.config import settings
from app.api.v1.api import api_router
from app.api.v1.routers.health import router as health_router

try:
    from prometheus_fastapi_instrumentator import Instrumentator
except ImportError:
    Instrumentator = None

import routers.gpt_router

# Configurar structlog
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

# Mensajes de error centralizados
ERROR_MESSAGES = {
    "GENERIC": "Error interno del servidor",
    "INVALID_TOKEN": "Token de autenticación inválido",
    "PRODUCT_SEARCH_ERROR": "No se pudo buscar productos",
    "OPTIMIZE_ERROR": "No se pudo optimizar la lista de compras",
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Iniciando aplicación Cuanto Cuesta...")

    redis_url = settings.REDIS_URL
    safe_url = redis_url.split("@")[-1] if redis_url else ""
    if not redis_url or ("localhost" in redis_url and not settings.DEBUG):
        logger.error("REDIS_URL inválida", redis_url=safe_url)
        raise RuntimeError("Invalid REDIS_URL")

    redis = aioredis.from_url(redis_url, encoding="utf-8", decode_responses=True)
    try:
        await redis.ping()
    except Exception as exc:  # pragma: no cover - network failure
        logger.error("No se pudo conectar a Redis", redis_url=safe_url, error=str(exc))
        raise RuntimeError("Redis ping failed") from exc

    app.state.redis = redis
    if FastAPILimiter:
        # Initialize limiter with shared Redis client
        await FastAPILimiter.init(app.state.redis)

    try:
        yield
    finally:
        await redis.close()
        logger.info("Cerrando aplicación...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="""
    API REST para comparación de precios de supermercados chilenos.
    ... (tu descripción aquí) ...
    """,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS y TrustedHosts
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
if not settings.DEBUG:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)

# Middleware de logging y métricas
@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    user_id = request.headers.get("X-User-ID", "anonymous")
    bind_contextvars(request_id=request_id, user_id=user_id)

    start = time.time()
    logger.info("Request", method=request.method, url=str(request.url))
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("Error procesando request")
        clear_contextvars()
        raise

    elapsed = round(time.time() - start, 3)
    logger.info("Response", status_code=response.status_code, process_time=elapsed, path=request.url.path)
    response.headers["X-Process-Time"] = str(elapsed)
    clear_contextvars()
    return response

# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.status_code,
                "message": exc.detail or ERROR_MESSAGES["GENERIC"],
                "path": str(request.url.path),
            },
            "timestamp": time.time(),
        },
    )

@app.exception_handler(OpenAIError)
async def openai_exception_handler(request: Request, exc: OpenAIError):
    logger.exception("Error en OpenAI")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": 500,
                "message": ERROR_MESSAGES["GENERIC"],
                "path": str(request.url.path),
            },
            "timestamp": time.time(),
        },
    )

@app.exception_handler(RedisError)
async def redis_exception_handler(request: Request, exc: RedisError):
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
    logger.exception("Error no manejado")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": 500,
                "message": ERROR_MESSAGES["GENERIC"],
                "path": str(request.url.path),
            },
            "timestamp": time.time(),
        },
    )

# Routers
app.include_router(health_router)
app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(routers.gpt_router.router)

# Prometheus metrics
if Instrumentator:
    Instrumentator().instrument(app).expose(app)

# OpenAPI custom
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=settings.PROJECT_NAME,
        version=settings.PROJECT_VERSION,
        description=app.description,
        routes=app.routes,
    )
    base = settings.BASE_URL or "https://cuantocuestabackend.onrender.com"
    schema["servers"] = [{"url": base}]
    schema["info"].update({
        "x-logo": {"url": "https://cuantocuesta.cl/logo.png"},
        "contact": {"name": "Equipo Cuanto Cuesta", "email": "api@cuantocuesta.cl", "url": "https://cuantocuesta.cl"},
        "license": {"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
    })
    schema["tags"] = [
        {"name": "Productos", "description": "Búsqueda y gestión de productos"},
        {"name": "Precios", "description": "Comparación y análisis de precios"},
        {"name": "Tiendas", "description": "Búsqueda geográfica de tiendas"},
        {"name": "Health", "description": "Monitoreo y estado del sistema"},
    ]
    app.openapi_schema = schema
    return schema

app.openapi = custom_openapi

# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "¡Bienvenido a Cuanto Cuesta API!",
        "version": settings.PROJECT_VERSION,
        "health_url": "/health",
        "docs_url": "/docs",
        "features": [
            "Búsqueda inteligente", "Comparación en tiempo real",
            "Geolocalización con PostGIS", "Manejo de caracteres especiales",
            "Optimización de listas", "API multi-plataforma"
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
