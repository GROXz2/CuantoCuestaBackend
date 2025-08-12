import asyncio
import os
import types

os.environ["OPENAI_API_KEY"] = "test-key"
import openai_client  # noqa: E402


def test_consulta_gpt(monkeypatch):
    class DummyResponse:
        output_text = "Hola Mundo "

    async def fake_create(**kwargs):
        return DummyResponse()

    dummy_client = types.SimpleNamespace(
        responses=types.SimpleNamespace(create=fake_create)
    )

    monkeypatch.setattr(openai_client, "client", dummy_client)

    result = asyncio.run(openai_client.consulta_gpt("Hola?"))
    assert result == "Hola Mundo"


def test_consulta_gpt_sin_clave(monkeypatch):
    monkeypatch.setattr(openai_client, "client", None)
    result = asyncio.run(openai_client.consulta_gpt("Hola?"))
    assert "no configurada" in result.lower()


def test_consulta_gpt_auth_error(monkeypatch):
    class DummyAuthError(openai_client.AuthenticationError):
        def __init__(self):
            pass

    async def fake_create(**kwargs):
        raise DummyAuthError()

    dummy_client = types.SimpleNamespace(
        responses=types.SimpleNamespace(create=fake_create)
    )
    monkeypatch.setattr(openai_client, "client", dummy_client)
    result = asyncio.run(openai_client.consulta_gpt("Hola?"))
    assert "autenticaci" in result.lower()


def test_consulta_gpt_timeout(monkeypatch):
    async def fake_create(**kwargs):
        raise asyncio.TimeoutError()

    dummy_client = types.SimpleNamespace(
        responses=types.SimpleNamespace(create=fake_create)
    )
    monkeypatch.setattr(openai_client, "client", dummy_client)
    result = asyncio.run(openai_client.consulta_gpt("Hola?"))
    assert "tiempo de espera" in result.lower()


def test_consulta_gpt_openai_error(monkeypatch):
    async def fake_create(**kwargs):
        raise openai_client.OpenAIError("boom")

    dummy_client = types.SimpleNamespace(
        responses=types.SimpleNamespace(create=fake_create)
    )
    monkeypatch.setattr(openai_client, "client", dummy_client)
    result = asyncio.run(openai_client.consulta_gpt("Hola?"))
    assert "error al consultar" in result.lower()


def test_consulta_gpt_generic_error(monkeypatch):
    async def fake_create(**kwargs):
        raise ValueError("fail")

    dummy_client = types.SimpleNamespace(
        responses=types.SimpleNamespace(create=fake_create)
    )
    monkeypatch.setattr(openai_client, "client", dummy_client)
    result = asyncio.run(openai_client.consulta_gpt("Hola?"))
    assert "búsqueda web" in result.lower()
