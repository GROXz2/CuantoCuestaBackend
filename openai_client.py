# openai_client.py
import os
import structlog
from openai import OpenAI, OpenAIError

logger = structlog.get_logger(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def consulta_gpt(prompt: str) -> str:
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except OpenAIError:
        logger.exception("Error consultando a OpenAI")
        raise
