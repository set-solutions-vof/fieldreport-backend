from io import BytesIO

from PIL import Image

from src.utils.images import normalize_to_jpeg


def test_normalize_to_jpeg_returns_original_for_non_heic() -> None:
    data = b"image-data"

    result = normalize_to_jpeg(data, "photo.png", "image/png")

    assert result == (data, ".png", "image/png")


def test_normalize_to_jpeg_converts_heif_content_type() -> None:
    buffer = BytesIO()
    Image.new("RGB", (1, 1), color="red").save(buffer, format="PNG")

    data, suffix, content_type = normalize_to_jpeg(
        buffer.getvalue(),
        "photo",
        "image/heif",
    )

    assert data.startswith(b"\xff\xd8")
    assert suffix == ".jpg"
    assert content_type == "image/jpeg"
