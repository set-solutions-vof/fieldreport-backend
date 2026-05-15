from openai import AsyncOpenAI
from openai.types.shared_params.response_format_json_object import ResponseFormatJSONObject

from src.config import settings
from src.llm.client_factory import create_openai_compatible_client
from src.models.templates.configuration import TemplateSection
from src.models.templates.pipeline import (
    TemplateAnalysisDocument,
    TemplateAnalysisDocumentList,
    TemplateSectionList,
)
from src.prompts.deepseek_template_extraction import (
    DEEPSEEK_TEMPLATE_EXTRACTION_PROMPT,
    DEEPSEEK_TEMPLATE_EXTRACTION_SYSTEM_PROMPT,
)


def get_deepseek_client() -> AsyncOpenAI:
    return create_openai_compatible_client(settings.deepseek_endpoint, settings.deepseek_api_key)


def build_template_analysis_prompt(documents: list[TemplateAnalysisDocument]) -> str:
    documents_json = TemplateAnalysisDocumentList(documents=documents).model_dump_json(
        ensure_ascii=True
    )

    return DEEPSEEK_TEMPLATE_EXTRACTION_PROMPT.format(documents_json=documents_json)


async def synthesize_template_sections(
    documents: list[TemplateAnalysisDocument],
) -> list[TemplateSection]:
    client = get_deepseek_client()
    response = await client.chat.completions.create(
        model=settings.deepseek_deployment,
        messages=[
            {
                "role": "system",
                "content": DEEPSEEK_TEMPLATE_EXTRACTION_SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": build_template_analysis_prompt(documents),
            },
        ],
        response_format=ResponseFormatJSONObject(type="json_object"),
    )
    content = response.choices[0].message.content or ""
    payload = TemplateSectionList.model_validate_json(content)

    return payload.sections
