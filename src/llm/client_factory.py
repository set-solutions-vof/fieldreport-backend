from openai import AsyncOpenAI

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


def get_gpt4o_transcribe_client() -> AsyncOpenAI:
    return create_openai_compatible_client(
        settings.azure_openai_endpoint,
        settings.azure_openai_api_key,
    )
