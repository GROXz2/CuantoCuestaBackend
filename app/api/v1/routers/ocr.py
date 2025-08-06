"""Router OCR para extraer lista de productos desde imágenes"""
import logging
import time
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.ocr_service import ocr_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/lista")
async def obtener_lista_ocr(
    images: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """Procesa imágenes y retorna lista de productos detectados"""
    start_time = time.time()
    productos = []
    try:
        for image in images:
            content = await image.read()
            productos.extend(ocr_service.extract_products_from_image(content, db))
        return {"productos": productos}
    except Exception as exc:
        logger.error("Error en endpoint OCR: %s", exc)
        raise HTTPException(status_code=500, detail="Error procesando imágenes")
    finally:
        logger.info("Procesamiento OCR completado en %.3fs", time.time() - start_time)
