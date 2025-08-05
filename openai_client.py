# openai_client.py
import os
from typing import Optional
from openai import OpenAI, OpenAIError

_api_key = os.getenv("OPENAI_API_KEY")
client: Optional[OpenAI] = OpenAI(api_key=_api_key) if _api_key else None


def consulta_gpt(prompt: str) -> str:
    if client is None:
        raise OpenAIError("OPENAI_API_KEY no configurado")
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()
