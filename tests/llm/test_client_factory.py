from unittest.mock import patch

from src.llm import client_factory


def test_get_gpt4o_client_returns_configured_client() -> None:
    client = object()

    with (
        patch.object(
            client_factory.settings, "azure_openai_endpoint", "https://ai.example/openai/v1/"
        ),
        patch.object(client_factory.settings, "azure_openai_api_key", "shared-key"),
        patch.object(client_factory, "AsyncOpenAI", return_value=client) as factory,
    ):
        result = client_factory.get_gpt4o_client()

    assert result is client
    factory.assert_called_once_with(
        base_url="https://ai.example/openai/v1/",
        api_key="shared-key",
    )


def test_get_deepseek_client_returns_configured_client() -> None:
    client = object()

    with (
        patch.object(
            client_factory.settings, "azure_openai_endpoint", "https://ai.example/openai/v1/"
        ),
        patch.object(client_factory.settings, "azure_openai_api_key", "shared-key"),
        patch.object(client_factory, "AsyncOpenAI", return_value=client) as factory,
    ):
        result = client_factory.get_deepseek_client()

    assert result is client
    factory.assert_called_once_with(
        base_url="https://ai.example/openai/v1/",
        api_key="shared-key",
    )


def test_get_gpt4o_transcribe_client_returns_configured_client() -> None:
    client = object()

    with (
        patch.object(
            client_factory.settings,
            "azure_openai_resource_endpoint",
            "https://ai.example",
        ),
        patch.object(client_factory.settings, "azure_openai_api_key", "shared-key"),
        patch.object(client_factory.settings, "gpt4o_transcribe_api_version", "2024-10-21"),
        patch.object(client_factory, "AsyncAzureOpenAI", return_value=client) as factory,
    ):
        result = client_factory.get_gpt4o_transcribe_client()

    assert result is client
    factory.assert_called_once_with(
        azure_endpoint="https://ai.example",
        api_key="shared-key",
        api_version="2024-10-21",
    )
