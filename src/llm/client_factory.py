from openai import AsyncAzureOpenAI, AsyncOpenAI


def create_openai_compatible_client(base_url: str, api_key: str) -> AsyncOpenAI:
    return AsyncOpenAI(base_url=base_url, api_key=api_key)


def create_azure_openai_client(endpoint: str, api_key: str, api_version: str) -> AsyncAzureOpenAI:
    return AsyncAzureOpenAI(azure_endpoint=endpoint, api_key=api_key, api_version=api_version)
