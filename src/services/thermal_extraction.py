import subprocess
import tempfile
from pathlib import Path

import numpy as np
from pydantic import BaseModel
from scipy import signal


class PanelThermalMetrics(BaseModel):
    panel_index: int
    row: int
    col: int
    tmin_c: float
    tmax_c: float
    tgem_c: float
    delta_t_c: float
    bbox: tuple[int, int, int, int]  # r0, c0, r1, c1


class ThermalMetrics(BaseModel):
    panels: list[PanelThermalMetrics]


_SENSOR_W = 640
_SENSOR_H = 512
_EXPECTED_BYTES = _SENSOR_W * _SENSOR_H * 2

# Frame rails (aluminum) read artificially cold due to low emissivity.
# Panel glass pixels are always well above this floor.
_FRAME_THRESHOLD_C = 38.0
_MIN_PANEL_PIXELS = 500  # ~22x22, rejects tiny edge slices
_MIN_REGION_SIZE = 60  # pixels — grid slice must be at least this wide/tall


def _grid_lines(profile: np.ndarray, min_distance: int = 50, prominence: float = 8.0) -> np.ndarray:
    smoothed = np.convolve(profile, np.ones(5) / 5, mode="same")
    valleys, _ = signal.find_peaks(-smoothed, prominence=prominence, distance=min_distance)
    return valleys


def _regions(lines: np.ndarray, total: int) -> list[tuple[int, int]]:
    edges = [0, *lines.tolist(), total]
    return [
        (edges[i], edges[i + 1])
        for i in range(len(edges) - 1)
        if edges[i + 1] - edges[i] >= _MIN_REGION_SIZE
    ]


def _panel_metrics(
    temps: np.ndarray, r0: int, r1: int, c0: int, c1: int
) -> tuple[float, float, float, float] | None:
    region = temps[r0:r1, c0:c1]
    # Exclude frame rail pixels — they are emissivity artifacts, not panel temperature
    panel_pixels = region[region > _FRAME_THRESHOLD_C]
    if panel_pixels.size < _MIN_PANEL_PIXELS:
        return None
    tmax = float(panel_pixels.max())
    tgem = float(panel_pixels.mean())
    return (
        round(float(panel_pixels.min()), 1),
        round(tmax, 1),
        round(tgem, 1),
        round(tmax - tgem, 1),
    )


def _is_rooftop(temps: np.ndarray, r0: int, r1: int) -> bool:
    # Panel rows have horizontal frame rails creating cold pixels across the full width.
    # Rooftop rows only have cold pixels at the vertical frame rail columns — far fewer.
    cold_fraction = (temps[r0:r1, :] < _FRAME_THRESHOLD_C).mean()
    return cold_fraction < 0.001


def extract_thermal_metrics(image_bytes: bytes) -> ThermalMetrics | None:
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
        f.write(image_bytes)
        tmp = Path(f.name)

    try:
        raw = subprocess.check_output(
            ["exiftool", "-b", "-ThermalData", str(tmp)],
            stderr=subprocess.DEVNULL,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    finally:
        tmp.unlink(missing_ok=True)

    if len(raw) != _EXPECTED_BYTES:
        return None

    temps = (
        np.frombuffer(raw, dtype="<u2").astype(np.float32).reshape(_SENSOR_H, _SENSOR_W) / 64.0
        - 273.15
    )

    col_lines = _grid_lines(temps.min(axis=0))
    row_lines = _grid_lines(temps.min(axis=1))

    col_regions = _regions(col_lines, _SENSOR_W)
    row_regions = _regions(row_lines, _SENSOR_H)

    panels: list[PanelThermalMetrics] = []
    panel_index = 1

    for ri, (r0, r1) in enumerate(row_regions):
        if _is_rooftop(temps, r0, r1):
            continue

        for ci, (c0, c1) in enumerate(col_regions):
            result = _panel_metrics(temps, r0, r1, c0, c1)
            if result is None:
                continue

            tmin, tmax, tgem, delta_t = result
            panels.append(
                PanelThermalMetrics(
                    panel_index=panel_index,
                    row=ri,
                    col=ci,
                    tmin_c=tmin,
                    tmax_c=tmax,
                    tgem_c=tgem,
                    delta_t_c=delta_t,
                    bbox=(r0, c0, r1, c1),
                )
            )
            panel_index += 1

    if not panels:
        return None

    return ThermalMetrics(panels=panels)
