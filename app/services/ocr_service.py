"""Servicio OCR para extraer texto de imágenes"""
import io
import logging
import time
import unicodedata
from typing import List

try:
    from PIL import Image
    import pytesseract
except Exception:  # pragma: no cover - dependencias opcionales
    Image = None
    pytesseract = None

from sqlalchemy.orm import Session

from app.services.product_service import product_service

logger = logging.getLogger(__name__)


class OCRService:
    """Servicio que utiliza Tesseract para extraer texto de imágenes"""

    @staticmethod
    def _check_dependencies() -> None:
        if Image is None or pytesseract is None:
            raise RuntimeError("pytesseract y pillow son requeridos para OCR")

    @staticmethod
    def normalize_text(text: str) -> str:
        """Normaliza texto eliminando acentos y convirtiendo a mayúsculas"""
        normalized = unicodedata.normalize("NFKD", text)
        without_accents = "".join(c for c in normalized if not unicodedata.combining(c))
        return without_accents.upper()

    def extract_text(self, image_bytes: bytes) -> str:
        """Extrae texto desde una imagen usando Tesseract"""
        self._check_dependencies()
        start_time = time.time()
        try:
            image = Image.open(io.BytesIO(image_bytes))
            text = pytesseract.image_to_string(image, lang="spa")
            normalized = self.normalize_text(text)
            logger.info("OCR procesado en %.3fs", time.time() - start_time)
            return normalized
        except Exception as exc:  # pragma: no cover - errores de OCR
            logger.error("Error procesando imagen OCR: %s", exc)
            raise

    def extract_products_from_image(self, image_bytes: bytes, db: Session) -> List[dict]:
        """Obtiene productos coincidentes a partir del texto extraído"""
        text = self.extract_text(image_bytes)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        products: List[dict] = []
        for line in lines:
            result = product_service.search_products(db, line, limite=1)
            if result.get("productos"):
                products.append(result["productos"][0])
        return products


# Instancia global del servicio
ocr_service = OCRService()
