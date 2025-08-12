import types
import pytest
import asyncio

import openai_client


@pytest.mark.asyncio
async def test_consulta_gpt_success(monkeypatch):
    class DummyChoice:
        def __init__(self, content: str):
            self.message = types.SimpleNamespace(content=content)

    class DummyResponse:
        choices = [DummyChoice("Hola Mundo ")]

    async def fake_create(**kwargs):
        return DummyResponse()

    dummy_client = types.SimpleNamespace(
        chat=types.SimpleNamespace(
            completions=types.SimpleNamespace(create=fake_create)
        )
    )

    monkeypatch.setattr(openai_client, "client", dummy_client)

    result = await openai_client.consulta_gpt("Hola?")
    assert result == "Hola Mundo"


@pytest.mark.asyncio
async def test_consulta_gpt_no_client(monkeypatch):
    monkeypatch.setattr(openai_client, "client", None)
    result = await openai_client.consulta_gpt("Hola?")
    assert "OPENAI_API_KEY" in result


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "exc,expected",
    [
        (
            type("DummyAuthError", (openai_client.AuthenticationError,), {"__init__": lambda self: Exception.__init__(self, "auth")})(),
            "Error de autenticación con OpenAI.",
        ),
        (
            asyncio.TimeoutError(),
            "La solicitud a OpenAI excedió el tiempo de espera.",
        ),
        (
            type("DummyOpenAIError", (openai_client.OpenAIError,), {"__init__": lambda self: Exception.__init__(self, "boom")})(),
            "Ocurrió un error al consultar el modelo.",
        ),
    ],
)
async def test_consulta_gpt_errors(monkeypatch, exc, expected):
    async def fake_create(**kwargs):
        raise exc

    dummy_client = types.SimpleNamespace(
        chat=types.SimpleNamespace(
            completions=types.SimpleNamespace(create=fake_create)
        )
    )

    monkeypatch.setattr(openai_client, "client", dummy_client)

    result = await openai_client.consulta_gpt("Hola?")
    assert result == expected
