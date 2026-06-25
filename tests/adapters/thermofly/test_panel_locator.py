import os
import tempfile

import pytest

from src.adapters.thermofly.panel_locator import generate_panel_location_image

FLIGHT_DIR = "/Users/florianterlinden/Desktop/SET/LEKK/ThermoFlyy/vluchtfotos_2"
OVERVIEW = f"{FLIGHT_DIR}/DJI_20260625134718_0001_V.JPG"
PANEL_10 = f"{FLIGHT_DIR}/DJI_20260625135023_0010_V.JPG"

# Visually verified: marker lands on the solar panel array (center-right roof section).
# Tolerance 50px at 4032x3024 resolution ≈ 1.2% of frame width.
EXPECTED_U = 2203
EXPECTED_V = 1672
TOLERANCE_PX = 50


@pytest.fixture(autouse=True)
def require_fixtures():
    if not os.path.exists(OVERVIEW) or not os.path.exists(PANEL_10):
        pytest.skip("Flight photo fixtures not present")


def test_panel_10_projects_onto_roof():
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
        out = f.name
    try:
        u, v = generate_panel_location_image(OVERVIEW, PANEL_10, out)
        assert abs(u - EXPECTED_U) <= TOLERANCE_PX, f"u={u} off by {abs(u - EXPECTED_U)}px"
        assert abs(v - EXPECTED_V) <= TOLERANCE_PX, f"v={v} off by {abs(v - EXPECTED_V)}px"
        assert os.path.getsize(out) > 10_000, "output JPEG suspiciously small"
    finally:
        os.unlink(out)


def test_output_image_is_cropped():
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
        out = f.name
    try:
        from PIL import Image

        generate_panel_location_image(OVERVIEW, PANEL_10, out, zoom_fraction=0.25)
        img = Image.open(out)
        # crop is zoom_fraction * IMG_W square (clamped); must be smaller than full frame
        assert img.width < 4032
        assert img.height < 3024
    finally:
        os.unlink(out)


def test_missing_xmp_raises():
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
        f.write(b"\xff\xd8\xff\xe0" + b"\x00" * 100)
        bad = f.name
    try:
        with pytest.raises(ValueError, match="No DJI XMP"):
            generate_panel_location_image(bad, PANEL_10, "/dev/null")
    finally:
        os.unlink(bad)
