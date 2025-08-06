import time
import logging
from app.core.database import SessionLocal
from app.repositories.product_repository import product_repository
from app.services.price_service import price_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

INTERVAL_SECONDS = 60 * 60  # check every hour

def run_cycle() -> None:
    db = SessionLocal()
    try:
        products = product_repository.get_multi_active(db)
        for product in products:
            price_service.needs_rescrape(db, product.id)
    finally:
        db.close()

if __name__ == "__main__":
    while True:
        logger.info("Iniciando ciclo de verificación de scraping")
        run_cycle()
        logger.info("Ciclo completado, esperando próxima ejecución")
        time.sleep(INTERVAL_SECONDS)
