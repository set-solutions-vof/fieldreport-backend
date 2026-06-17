import io

import pillow_heif
from PIL import Image

pillow_heif.register_heif_opener()


def normalize_to_jpeg(data: bytes, content_type: str) -> tuple[bytes, str]:
    if content_type.lower() in {"image/heic", "image/heif", "image/heic-sequence"}:
        buffer = io.BytesIO()
        Image.open(io.BytesIO(data)).convert("RGB").save(buffer, format="JPEG", quality=95)
        return buffer.getvalue(), "image/jpeg"
    return data, content_type
