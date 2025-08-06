"""Tareas asíncronas reutilizando servicios existentes."""
from uuid import UUID

from tasks import background_queue  # noqa: F401, imported for side effects


def scrape_prices(product_id: UUID) -> dict:
    """Scrapea precios para un producto utilizando el servicio de precios."""
    from app.core.database import SessionLocal
    from app.services.price_service import price_service

    db = SessionLocal()
    try:
        # Se reutiliza el servicio existente para obtener/comparar precios
        return price_service.compare_prices(db, product_id)
    finally:
        db.close()


def process_shopping_image(file_id: str) -> str:
    """Procesa una imagen de lista de compras usando el cliente de OpenAI."""
    from openai_client import consulta_gpt

    prompt = f"Procesa la imagen de compra con ID {file_id}"
    return consulta_gpt(prompt)
