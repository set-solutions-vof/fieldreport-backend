from openai import AsyncAzureOpenAI, AsyncOpenAI

from src.config import settings


def create_openai_compatible_client(base_url: str, api_key: str) -> AsyncOpenAI:
    return AsyncOpenAI(base_url=base_url, api_key=api_key)


def get_gpt4o_client() -> AsyncOpenAI:
    return create_openai_compatible_client(
        settings.azure_openai_endpoint,
        settings.azure_openai_api_key,
    )


def get_deepseek_client() -> AsyncOpenAI:
    return create_openai_compatible_client(
        settings.azure_openai_endpoint,
        settings.azure_openai_api_key,
    )


def get_gpt4o_transcribe_client() -> AsyncAzureOpenAI:
    return AsyncAzureOpenAI(
        azure_endpoint=settings.azure_openai_resource_endpoint,
        api_key=settings.azure_openai_api_key,
        api_version=settings.gpt4o_transcribe_api_version,
    )
