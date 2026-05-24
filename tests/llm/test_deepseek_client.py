from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from src.llm import deepseek_client
from src.models.templates.pipeline import TemplateAnalysisDocument


def build_documents() -> list[TemplateAnalysisDocument]:
    return [
        TemplateAnalysisDocument(
            file_name="report.pdf",
            extracted_text="Summary text",
            visual_summary="Visual summary",
        )
    ]


def test_get_deepseek_client_returns_configured_client() -> None:
    client = object()

    with (
        patch.object(
            deepseek_client.settings, "deepseek_endpoint", "https://deepseek.example/openai/v1/"
        ),
        patch.object(deepseek_client.settings, "deepseek_api_key", "deepseek-key"),
        patch.object(
            deepseek_client, "create_openai_compatible_client", return_value=client
        ) as factory,
    ):
        result = deepseek_client.get_deepseek_client()

    assert result is client
    factory.assert_called_once_with(
        "https://deepseek.example/openai/v1/",
        "deepseek-key",
    )


def test_build_template_analysis_prompt_embeds_documents() -> None:
    prompt = deepseek_client.build_template_analysis_prompt(build_documents())

    assert "groups" in prompt
    assert '"documents":' in prompt
    assert '"file_name":"report.pdf"' in prompt
    assert '"visual_summary":"Visual summary"' in prompt


async def test_synthesize_template_sections_returns_validated_sections() -> None:
    create = AsyncMock(
        return_value=SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content='{"sections":[{"id":"summary","label":"Summary","render_type":"text_block"}]}'
                    )
                )
            ]
        )
    )
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))

    with (
        patch.object(deepseek_client, "get_deepseek_client", return_value=client),
        patch.object(deepseek_client.settings, "deepseek_deployment", "DeepSeek-V3.2-Speciale"),
    ):
        result = await deepseek_client.synthesize_template_sections(build_documents())

    assert [section.model_dump(exclude_none=True) for section in result] == [
        {
            "id": "summary",
            "label": "Summary",
            "order": 0,
            "render_type": "text_block",
            "found_in": 0,
        }
    ]
    assert create.await_args.kwargs["response_format"] == {"type": "json_object"}


async def test_synthesize_template_sections_raises_for_invalid_json() -> None:
    client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(
                create=AsyncMock(
                    return_value=SimpleNamespace(
                        choices=[SimpleNamespace(message=SimpleNamespace(content="not-json"))]
                    )
                )
            )
        )
    )

    with patch.object(deepseek_client, "get_deepseek_client", return_value=client):
        try:
            await deepseek_client.synthesize_template_sections(build_documents())
        except Exception as error:
            message = str(error)
        else:
            raise AssertionError("Expected JSON parsing or validation error")

    assert "json_invalid" in message.lower() or "invalid json" in message.lower()
