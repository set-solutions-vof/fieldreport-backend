from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from src.llm import gpt4o_client


def build_openai_message(content: str) -> SimpleNamespace:
    return SimpleNamespace(content=content, model_dump=lambda: {"content": content})


async def test_analyze_inspection_photo_returns_description() -> None:
    message = build_openai_message("Vochtplek zichtbaar op de wand.")
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
