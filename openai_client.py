"""Cliente asíncrono para interactuar con la API de OpenAI."""

import asyncio
import logging
import os
from typing import Optional

from openai import AsyncOpenAI, AuthenticationError, OpenAIError

logger = logging.getLogger(__name__)

API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")

client: Optional[AsyncOpenAI] = None
if API_KEY:
    client = AsyncOpenAI(api_key=API_KEY)
else:
    logger.error(
        "OPENAI_API_KEY no configurada. El cliente de OpenAI no fue inicializado."
    )


async def consulta_gpt(prompt: str) -> str:
    """Realiza una consulta al modelo GPT.

    Si no hay clave de API configurada o ocurre algún error, 
    se retorna un mensaje descriptivo y se registra el incidente en el log.
    """
    if client is None:
        return "OPENAI_API_KEY no configurada. No se pudo realizar la consulta."

    try:
        response = await client.responses.create(
            model="gpt-4o",
            input=prompt,
            temperature=0.7,
            connectors=[{"id": "web-search"}],
        )
        return response.output_text.strip()
    except AuthenticationError as exc:
        logger.error("Error de autenticación con OpenAI: %s", exc)
        return "Error de autenticación con OpenAI."
    except (asyncio.TimeoutError, TimeoutError) as exc:
        logger.error("La solicitud a OpenAI excedió el tiempo de espera: %s", exc)
        return "La solicitud a OpenAI excedió el tiempo de espera."
    except OpenAIError as exc:
        logger.error("Error de OpenAI: %s", exc)
        return "Ocurrió un error al consultar el modelo."
    except Exception as exc:
        logger.error("Error al realizar la búsqueda web: %s", exc)
        return "La búsqueda web falló o devolvió un formato inesperado."
