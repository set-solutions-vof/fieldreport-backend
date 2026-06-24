import base64
import mimetypes

from src.config import settings
from src.llm.client_factory import get_gpt4o_client
from src.prompts.image_analysis import IMAGE_ANALYSIS_PROMPT


async def analyze_inspection_photo(
    original_file_name: str,
    file_content: bytes,
    prompt: str = IMAGE_ANALYSIS_PROMPT,
) -> str:
    client = get_gpt4o_client()
    encoded_file = base64.b64encode(file_content).decode("utf-8")
    mime_type = mimetypes.guess_type(original_file_name)[0]

    response = await client.chat.completions.create(
        model=settings.gpt4o_deployment,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt,
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

    return response.choices[0].message.model_dump()["content"]
