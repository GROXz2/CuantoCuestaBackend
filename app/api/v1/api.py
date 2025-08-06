"""Router principal de la API v1"""
from fastapi import APIRouter

from app.api.v1.endpoints import productos, tiendas, precios, admin
from app.api.v1.routers import ocr

api_router = APIRouter()

# Incluir routers de endpoints
api_router.include_router(
    productos.router, 
    prefix="/productos", 
    tags=["Productos"]
)

api_router.include_router(
    tiendas.router, 
    prefix="/tiendas", 
    tags=["Tiendas"]
)

api_router.include_router(
    precios.router,
    prefix="/precios",
    tags=["Precios"]
)

# Admin: endpoints de administración
api_router.include_router(
    admin.router,
    prefix="/admin",
    tags=["Admin"]
)

# OCR: nuevos endpoints de reconocimiento
api_router.include_router(
    ocr.router,
    prefix="/ocr",
    tags=["OCR"]
)
