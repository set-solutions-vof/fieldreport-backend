from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from src.llm import deepseek_client
from src.models.templates.pipeline import TemplateAnalysisDocument


class FakeOpenAIMessage:
    def __init__(self, content: str):
        self.content = content

    def model_dump(self) -> dict[str, str]:
        return {"content": self.content}


def build_documents() -> list[TemplateAnalysisDocument]:
    return [
        TemplateAnalysisDocument(
            original_file_name="report.pdf",
            extracted_text="Summary text",
            visual_summary="Visual summary",
        )
    ]


async def test_synthesize_template_sections_returns_validated_sections() -> None:
    create = AsyncMock(
        return_value=SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=FakeOpenAIMessage(
                        '{"sections":[{"id":"summary","label":"Summary","render_type":"text_block"}]}'
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
    user_content = create.await_args.kwargs["messages"][1]["content"]
    assert "groups" in user_content
    assert '"documents":' in user_content
    assert '"original_file_name":"report.pdf"' in user_content
    assert '"visual_summary":"Visual summary"' in user_content


async def test_synthesize_template_sections_raises_for_invalid_json() -> None:
    client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(
                create=AsyncMock(
                    return_value=SimpleNamespace(
                        choices=[SimpleNamespace(message=FakeOpenAIMessage("not-json"))]
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
