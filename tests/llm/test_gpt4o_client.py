from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from src.llm import gpt4o_client


def test_get_gpt4o_client_returns_configured_client() -> None:
    client = object()

    with (
        patch.object(gpt4o_client.settings, "gpt4o_endpoint", "https://gpt4o.example/"),
        patch.object(gpt4o_client.settings, "gpt4o_api_key", "gpt4o-key"),
        patch.object(gpt4o_client.settings, "gpt4o_api_version", "2024-12-01-preview"),
        patch.object(gpt4o_client, "create_azure_openai_client", return_value=client) as factory,
    ):
        result = gpt4o_client.get_gpt4o_client()

    assert result is client
    factory.assert_called_once_with("https://gpt4o.example/", "gpt4o-key", "2024-12-01-preview")


def test_build_visual_analysis_schema_uses_visual_analysis_model_schema() -> None:
    schema = gpt4o_client.build_visual_analysis_schema()

    assert schema["type"] == "json_schema"
    assert schema["json_schema"]["name"] == "template_visual_analysis"
    assert schema["json_schema"]["strict"] is True


async def test_analyze_pdf_visuals_returns_normalized_json() -> None:
    message = SimpleNamespace(
        content=(
            '{"document_type":"inspection","visual_summary":"summary",'
            '"likely_sections":["summary"],"table_patterns":["key value"],'
            '"photo_expectations":["damage photo"]}'
        )
    )
    client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(
                create=AsyncMock(
                    return_value=SimpleNamespace(choices=[SimpleNamespace(message=message)])
                )
            )
        )
    )

    with (
        patch.object(gpt4o_client, "get_gpt4o_client", return_value=client),
        patch.object(gpt4o_client.settings, "gpt4o_deployment", "gpt-4o"),
    ):
        result = await gpt4o_client.analyze_pdf_visuals("report.pdf", b"pdf-bytes")

    assert result == (
        '{"document_type":"inspection","visual_summary":"summary",'
        '"likely_sections":["summary"],"table_patterns":["key value"],'
        '"photo_expectations":["damage photo"]}'
    )


async def test_analyze_pdf_visuals_raises_for_invalid_json() -> None:
    message = SimpleNamespace(content="oops")
    client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(
                create=AsyncMock(
                    return_value=SimpleNamespace(choices=[SimpleNamespace(message=message)])
                )
            )
        )
    )

    with patch.object(gpt4o_client, "get_gpt4o_client", return_value=client):
        try:
            await gpt4o_client.analyze_pdf_visuals("report.pdf", b"pdf-bytes")
        except ValueError as error:
            message_str = str(error)
        else:
            raise AssertionError("Expected ValueError")

    assert "Invalid JSON" in message_str or "expected value" in message_str.lower()
