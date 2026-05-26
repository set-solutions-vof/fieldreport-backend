from unittest.mock import patch

from openai import AsyncOpenAI

from src.llm import client_factory


def test_create_openai_compatible_client_returns_async_openai() -> None:
    client = client_factory.create_openai_compatible_client("https://example.com/v1/", "test-key")

    assert isinstance(client, AsyncOpenAI)


def test_get_gpt4o_client_returns_configured_client() -> None:
    client = object()

    with (
        patch.object(
            client_factory.settings, "azure_openai_endpoint", "https://ai.example/openai/v1/"
        ),
        patch.object(client_factory.settings, "azure_openai_api_key", "shared-key"),
        patch.object(
            client_factory,
            "create_openai_compatible_client",
            return_value=client,
        ) as factory,
    ):
        result = client_factory.get_gpt4o_client()

    assert result is client
    factory.assert_called_once_with("https://ai.example/openai/v1/", "shared-key")


def test_get_deepseek_client_returns_configured_client() -> None:
    client = object()

    with (
        patch.object(
            client_factory.settings, "azure_openai_endpoint", "https://ai.example/openai/v1/"
        ),
        patch.object(client_factory.settings, "azure_openai_api_key", "shared-key"),
        patch.object(
            client_factory,
            "create_openai_compatible_client",
            return_value=client,
        ) as factory,
    ):
        result = client_factory.get_deepseek_client()

    assert result is client
    factory.assert_called_once_with("https://ai.example/openai/v1/", "shared-key")


def test_get_gpt4o_transcribe_client_returns_configured_client() -> None:
    client = object()

    with (
        patch.object(
            client_factory.settings, "azure_openai_endpoint", "https://ai.example/openai/v1/"
        ),
        patch.object(client_factory.settings, "azure_openai_api_key", "shared-key"),
        patch.object(
            client_factory,
            "create_openai_compatible_client",
            return_value=client,
        ) as factory,
    ):
        result = client_factory.get_gpt4o_transcribe_client()

    assert result is client
    factory.assert_called_once_with("https://ai.example/openai/v1/", "shared-key")
