"""Endpoints administrativos para disparar tareas en segundo plano."""
from uuid import UUID

from fastapi import APIRouter

from tasks import background_queue
from tasks.jobs import scrape_prices, process_shopping_image

router = APIRouter()


@router.post("/scrape-precios/{product_id}")
def trigger_scrape_prices(product_id: UUID):
    """Encola la tarea para scrappear precios de un producto."""
    job = background_queue.enqueue(scrape_prices, product_id)
    return {"job_id": job.id}


@router.post("/procesar-imagen/{file_id}")
def trigger_process_image(file_id: str):
    """Encola la tarea para procesar una imagen de compra."""
    job = background_queue.enqueue(process_shopping_image, file_id)
    return {"job_id": job.id}
