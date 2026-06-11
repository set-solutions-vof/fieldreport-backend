import io
from pathlib import Path

import pillow_heif
from PIL import Image

pillow_heif.register_heif_opener()


def normalize_to_jpeg(data: bytes, filename: str, content_type: str) -> tuple[bytes, str, str]:
    suffix = Path(filename).suffix.lower()
    if suffix in {".heic", ".heif"} or content_type.lower() in {"image/heic", "image/heif", "image/heic-sequence"}:
        buffer = io.BytesIO()
        Image.open(io.BytesIO(data)).convert("RGB").save(buffer, format="JPEG", quality=95)
        return buffer.getvalue(), ".jpg", "image/jpeg"
    return data, suffix, content_type
