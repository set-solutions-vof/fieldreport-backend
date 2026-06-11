from io import BytesIO

from PIL import Image

from src.utils.images import normalize_to_jpeg


def test_normalize_to_jpeg_returns_png_unchanged() -> None:
    buffer = BytesIO()
    Image.new("RGB", (1, 1), color="red").save(buffer, format="PNG")
    image_data = buffer.getvalue()

    data, content_type = normalize_to_jpeg(image_data, "image/png")

    assert data == image_data
    assert content_type == "image/png"


def test_normalize_to_jpeg_converts_heif_content_type() -> None:
    buffer = BytesIO()
    Image.new("RGB", (1, 1), color="red").save(buffer, format="PNG")

    data, content_type = normalize_to_jpeg(buffer.getvalue(), "image/heif")

    assert data.startswith(b"\xff\xd8")
    assert content_type == "image/jpeg"


def test_normalize_to_jpeg_returns_jpeg_unchanged() -> None:
    data, content_type = normalize_to_jpeg(b"jpeg-data", "image/jpeg")

    assert data == b"jpeg-data"
    assert content_type == "image/jpeg"
