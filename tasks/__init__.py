"""Inicializa la cola de tareas RQ.

Si RQ no está disponible (por ejemplo durante las pruebas sin dependencias),
se utiliza un stub que ejecuta las tareas de forma síncrona.
"""
from redis import Redis

try:  # pragma: no cover - simple fallback
    from rq import Queue  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    class Queue:  # type: ignore
        """Implementación mínima para entornos sin RQ instalado."""

        def __init__(self, *args, **kwargs):
            pass

        def enqueue(self, func, *args, **kwargs):
            result = func(*args, **kwargs)

            class _Job:  # pylint: disable=too-few-public-methods
                id = "local"
                return_value = result

            return _Job()

from app.core.config import settings

redis_conn = Redis.from_url(settings.REDIS_URL)
# Cola por defecto para tareas en segundo plano
background_queue: Queue = Queue("default", connection=redis_conn)

__all__ = ["background_queue"]
