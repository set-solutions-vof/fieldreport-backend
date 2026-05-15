import base64
from typing import cast

from openai import AsyncAzureOpenAI
from openai.types.chat.completion_create_params import ResponseFormat

from src.config import settings
from src.llm.client_factory import create_azure_openai_client
from src.models.templates.pipeline import TemplateVisualAnalysis
from src.prompts.gpt4o_pdf_analysis import GPT4O_PDF_ANALYSIS_PROMPT


def get_gpt4o_client() -> AsyncAzureOpenAI:
    return create_azure_openai_client(
        settings.gpt4o_endpoint, settings.gpt4o_api_key, settings.gpt4o_api_version
    )


def build_visual_analysis_schema() -> ResponseFormat:
    schema = TemplateVisualAnalysis.model_json_schema()
    schema["additionalProperties"] = False

    return cast(
        ResponseFormat,
        {
            "type": "json_schema",
            "json_schema": {
                "name": "template_visual_analysis",
                "schema": schema,
                "strict": True,
            },
        },
    )


async def analyze_pdf_visuals(file_name: str, file_content: bytes) -> str:
    client = get_gpt4o_client()
    encoded_file = base64.b64encode(file_content).decode("utf-8")

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
        response_format=build_visual_analysis_schema(),
    )
    content = response.choices[0].message.content or ""
    parsed_content = TemplateVisualAnalysis.model_validate_json(content)

    return parsed_content.model_dump_json()
