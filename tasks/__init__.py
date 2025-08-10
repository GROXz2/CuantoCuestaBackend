"""Inicializa la cola de tareas RQ.

Si RQ no está disponible o no hay REDIS_URL configurada,
se utiliza un stub que ejecuta las tareas de forma síncrona.
"""
from redis import asyncio as aioredis

from app.core.config import settings

try:  # pragma: no cover - simple fallback
    from rq import Queue  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    Queue = None  # type: ignore

if not settings.REDIS_URL or Queue is None:
    class Queue:  # type: ignore
        """Implementación mínima para entornos sin RQ o Redis."""

        def __init__(self, *args, **kwargs):
            pass

        def enqueue(self, func, *args, **kwargs):
            result = func(*args, **kwargs)

            class _Job:  # pylint: disable=too-few-public-methods
                id = "local"
                return_value = result

            return _Job()

    redis_conn = None
else:  # pragma: no cover - requiere RQ y Redis reales
    redis_conn = aioredis.from_url(
        settings.REDIS_URL, encoding="utf-8", decode_responses=True
    )

# Cola por defecto para tareas en segundo plano
background_queue: Queue = Queue("default", connection=redis_conn)

__all__ = ["background_queue"]
