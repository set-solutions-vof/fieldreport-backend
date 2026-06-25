import numpy as np
from PIL import Image, ImageDraw

from src.utils.dji_xmp import extract_dji_xmp

# DJI M4T visual camera intrinsics
# Derived from: focal_mm=6.72, sensor_width_mm=9.694, image_width_px=4032
# fx = (focal_mm / sensor_width_mm) * image_width_px
IMG_W = 4032
IMG_H = 3024
FX = FY = (6.72 / 9.694) * IMG_W  # 2795.0 px
CX = IMG_W / 2
CY = IMG_H / 2


def generate_panel_location_image(
    overview_path: str,
    panel_path: str,
    output_path: str,
    zoom_fraction: float = 0.15,
) -> tuple[int, int]:
    with open(overview_path, "rb") as f:
        ov_bytes = f.read()
    with open(panel_path, "rb") as f:
        panel_bytes = f.read()

    ov = extract_dji_xmp(ov_bytes)
    panel = extract_dji_xmp(panel_bytes)

    if ov is None:
        raise ValueError(f"No DJI XMP found in overview image: {overview_path}")
    if panel is None:
        raise ValueError(f"No DJI XMP found in panel image: {panel_path}")

    _require(ov.gps_latitude, "overview GpsLatitude")
    _require(ov.gps_longitude, "overview GpsLongitude")
    _require(ov.relative_altitude, "overview RelativeAltitude")
    _require(ov.gimbal_yaw_degree, "overview GimbalYawDegree")
    _require(ov.gimbal_pitch_degree, "overview GimbalPitchDegree")
    _require(panel.lrf_target_lat, "panel LRFTargetLat")
    _require(panel.lrf_target_lon, "panel LRFTargetLon")
    _require(panel.lrf_target_alt, "panel LRFTargetAlt")

    u, v = _project(ov, panel)

    if not (0 <= u < IMG_W and 0 <= v < IMG_H):
        raise ValueError(
            f"Panel projects outside overview frame (u={u}, v={v}) — "
            "check that the overview image covers the inspection area."
        )

    img = Image.open(overview_path)
    _annotate(img, u, v, zoom_fraction, output_path)

    return u, v


def _require(value: float | None, field: str) -> None:
    if value is None:
        raise ValueError(f"Missing required XMP field: {field}")


def _project(ov, panel) -> tuple[int, int]:
    yaw = np.radians(ov.gimbal_yaw_degree)
    pitch = np.radians(ov.gimbal_pitch_degree)

    x_cam = np.array([np.cos(yaw), -np.sin(yaw), 0.0])
    z_cam = np.array([np.cos(pitch) * np.sin(yaw), np.cos(pitch) * np.cos(yaw), np.sin(pitch)])
    y_cam = np.cross(z_cam, x_cam)
    R = np.array([x_cam, y_cam, z_cam])

    M_LAT = 111320.0
    M_LON = 111320.0 * np.cos(np.radians(ov.gps_latitude))

    # LRFTargetAlt is relative to the takeoff point (same datum as RelativeAltitude),
    # so delta-Z = panel_lrf_alt - overview_rel_alt.
    P_enu = np.array(
        [
            (panel.lrf_target_lon - ov.gps_longitude) * M_LON,
            (panel.lrf_target_lat - ov.gps_latitude) * M_LAT,
            panel.lrf_target_alt - ov.relative_altitude,
        ]
    )

    P_cam = R @ P_enu
    if P_cam[2] <= 0:
        raise ValueError("Panel is behind the overview camera — negative depth after projection.")

    u = int(FX * P_cam[0] / P_cam[2] + CX)
    v = int(FY * P_cam[1] / P_cam[2] + CY)
    return u, v


def _annotate(img: Image.Image, u: int, v: int, zoom_fraction: float, output_path: str) -> None:
    half = int(zoom_fraction * IMG_W / 2)
    x0 = max(0, u - half)
    y0 = max(0, v - half)
    x1 = min(IMG_W, u + half)
    y1 = min(IMG_H, v + half)
    cropped = img.crop((x0, y0, x1, y1))

    # Panel position relative to crop origin
    cu = u - x0
    cv = v - y0

    draw = ImageDraw.Draw(cropped)
    red = (220, 30, 30)
    arm = 90
    draw.line([cu - arm, cv, cu + arm, cv], fill=red, width=6)
    draw.line([cu, cv - arm, cu, cv + arm], fill=red, width=6)
    draw.ellipse([cu - 30, cv - 30, cu + 30, cv + 30], outline=red, width=4)

    cropped.save(output_path, "JPEG", quality=92)
