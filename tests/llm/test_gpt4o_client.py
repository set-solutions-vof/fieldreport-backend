from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from src.llm import gpt4o_client


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


async def test_analyze_inspection_photo_returns_description() -> None:
    message = SimpleNamespace(content="Vochtplek zichtbaar op de wand.")
    client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(
                create=AsyncMock(
                    return_value=SimpleNamespace(
                        choices=[SimpleNamespace(message=message)],
                        usage=SimpleNamespace(total_tokens=42),
                    )
                )
            )
        )
    )

    with (
        patch.object(gpt4o_client, "get_gpt4o_client", return_value=client),
        patch.object(gpt4o_client.settings, "gpt4o_deployment", "gpt-4o"),
    ):
        result = await gpt4o_client.analyze_inspection_photo("photo.jpg", b"image")

    assert result == "Vochtplek zichtbaar op de wand."
    request = client.chat.completions.create.await_args.kwargs
    assert request["model"] == "gpt-4o"
    assert request["messages"][0]["content"][1]["image_url"]["url"].startswith(
        "data:image/jpeg;base64,"
    )
