from openai.types.shared_params.response_format_json_object import ResponseFormatJSONObject

from src.config import settings
from src.llm.client_factory import get_deepseek_client
from src.models.templates.domain import TemplateSection, TemplateStructure
from src.models.templates.pipeline import (
    TemplateAnalysisDocument,
    TemplateAnalysisDocumentList,
)
from src.prompts.deepseek_template_extraction import (
    DEEPSEEK_TEMPLATE_EXTRACTION_PROMPT,
    DEEPSEEK_TEMPLATE_EXTRACTION_SYSTEM_PROMPT,
)


async def synthesize_template_sections(
    documents: list[TemplateAnalysisDocument],
) -> list[TemplateSection]:
    return (await synthesize_template_structure(documents)).sections


async def synthesize_template_structure(
    documents: list[TemplateAnalysisDocument],
) -> TemplateStructure:
    client = get_deepseek_client()
    documents_json = TemplateAnalysisDocumentList(documents=documents).model_dump_json()

    response = await client.chat.completions.create(
        model=settings.deepseek_deployment,
        messages=[
            {
                "role": "system",
                "content": DEEPSEEK_TEMPLATE_EXTRACTION_SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": DEEPSEEK_TEMPLATE_EXTRACTION_PROMPT.format(
                    documents_json=documents_json
                ),
            },
        ],
        response_format=ResponseFormatJSONObject(type="json_object"),
    )
    content = response.choices[0].message.model_dump()["content"]
    payload = TemplateStructure.model_validate_json(content)

    return payload
