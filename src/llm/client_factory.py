from openai import AsyncAzureOpenAI, AsyncOpenAI

from src.config import settings


def get_gpt4o_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        base_url=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
    )


def get_deepseek_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        base_url=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
    )


def get_gpt4o_transcribe_client() -> AsyncAzureOpenAI:
    return AsyncAzureOpenAI(
        azure_endpoint=settings.azure_openai_resource_endpoint,
        api_key=settings.azure_openai_api_key,
        api_version=settings.gpt4o_transcribe_api_version,
    )
