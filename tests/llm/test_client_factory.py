from openai import AsyncAzureOpenAI, AsyncOpenAI

from src.llm.client_factory import create_azure_openai_client, create_openai_compatible_client


def test_create_openai_compatible_client_returns_async_openai() -> None:
    client = create_openai_compatible_client("https://example.com/v1/", "test-key")

    assert isinstance(client, AsyncOpenAI)


def test_create_azure_openai_client_returns_async_azure_openai() -> None:
    client = create_azure_openai_client(
        "https://example.azure.com/", "test-key", "2024-12-01-preview"
    )

    assert isinstance(client, AsyncAzureOpenAI)
