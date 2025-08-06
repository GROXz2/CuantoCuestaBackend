import os
import types

os.environ["OPENAI_API_KEY"] = "test-key"
import openai_client  # noqa: E402


def test_consulta_gpt(monkeypatch):
    class DummyChoice:
        def __init__(self, content: str):
            self.message = types.SimpleNamespace(content=content)

    class DummyResponse:
        choices = [DummyChoice("Hola Mundo ")]

    def fake_create(**kwargs):
        return DummyResponse()

    dummy_client = types.SimpleNamespace(
        chat=types.SimpleNamespace(
            completions=types.SimpleNamespace(create=fake_create)
        )
    )

    monkeypatch.setattr(openai_client, "client", dummy_client)

    result = openai_client.consulta_gpt("Hola?")
    assert result == "Hola Mundo"
