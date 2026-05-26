import base64
import mimetypes

from openai.types.shared_params.response_format_json_schema import (
    JSONSchema,
    ResponseFormatJSONSchema,
)

from src.config import settings
from src.llm.client_factory import get_gpt4o_client
from src.models.templates.pipeline import TemplateVisualAnalysis
from src.prompts.gpt4o_pdf_analysis import GPT4O_PDF_ANALYSIS_PROMPT
from src.prompts.image_analysis import IMAGE_ANALYSIS_PROMPT


async def analyze_pdf_visuals(file_name: str, file_content: bytes) -> str:
    client = get_gpt4o_client()
    encoded_file = base64.b64encode(file_content).decode("utf-8")
    schema: dict[str, object] = TemplateVisualAnalysis.model_json_schema()
    schema["additionalProperties"] = False

    response = await client.chat.completions.create(
        model=settings.gpt4o_deployment,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "file",
                        "file": {
                            "filename": file_name,
                            "file_data": f"data:application/pdf;base64,{encoded_file}",
                        },
                    },
                    {
                        "type": "text",
                        "text": GPT4O_PDF_ANALYSIS_PROMPT,
                    },
                ],
            }
        ],
        response_format=ResponseFormatJSONSchema(
            type="json_schema",
            json_schema=JSONSchema(
                name="template_visual_analysis",
                schema=schema,
                strict=True,
            ),
        ),
    )
    content = response.choices[0].message.content
    assert content is not None
    parsed_content = TemplateVisualAnalysis.model_validate_json(content)

    return parsed_content.model_dump_json()


async def analyze_inspection_photo(file_name: str, file_content: bytes) -> str:
    client = get_gpt4o_client()
    encoded_file = base64.b64encode(file_content).decode("utf-8")
    mime_type = mimetypes.guess_type(file_name)[0]

    response = await client.chat.completions.create(
        model=settings.gpt4o_deployment,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": IMAGE_ANALYSIS_PROMPT,
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{encoded_file}",
                        },
                    },
                ],
            }
        ],
    )

    content = response.choices[0].message.content
    assert content is not None

    return content
