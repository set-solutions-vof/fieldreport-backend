from datetime import datetime
from xml.etree import ElementTree

from src.models.reports.dji_xmp import DjiXmpMetadata

_DJI_NS = "http://www.dji.com/drone-dji/1.0/"
_XMP_START = b"<x:xmpmeta"
_XMP_END = b"</x:xmpmeta>"


def extract_dji_xmp(file_content: bytes) -> DjiXmpMetadata | None:
    start = file_content.find(_XMP_START)
    if start == -1:
        return None
    end = file_content.find(_XMP_END, start)
    if end == -1:
        return None

    root = ElementTree.fromstring(file_content[start : end + len(_XMP_END)].decode("utf-8", errors="replace"))

    def get(tag: str) -> str | None:
        key = f"{{{_DJI_NS}}}{tag}"
        el = root.find(f".//{key}")
        if el is not None:
            return el.text
        for node in root.iter():
            if key in node.attrib:
                return node.attrib[key]
        return None

    def to_float(v: str | None) -> float | None:
        return float(v) if v is not None else None

    def to_int(v: str | None) -> int | None:
        return int(v) if v is not None else None

    def to_dt(v: str | None) -> datetime | None:
        return datetime.fromisoformat(v.replace("Z", "+00:00")) if v is not None else None

    return DjiXmpMetadata(
        utc_at_exposure=to_dt(get("UTCAtExposure")),
        gps_latitude=to_float(get("GpsLatitude")),
        gps_longitude=to_float(get("GpsLongitude")),
        absolute_altitude=to_float(get("AbsoluteAltitude")),
        relative_altitude=to_float(get("RelativeAltitude")),
        gimbal_pitch_degree=to_float(get("GimbalPitchDegree")),
        gimbal_yaw_degree=to_float(get("GimbalYawDegree")),
        gimbal_roll_degree=to_float(get("GimbalRollDegree")),
        lrf_target_lat=to_float(get("LRFTargetLat")),
        lrf_target_lon=to_float(get("LRFTargetLon")),
        lrf_target_alt=to_float(get("LRFTargetAlt")),
        lrf_target_distance=to_float(get("LRFTargetDistance")),
        image_source=get("ImageSource"),
        rtk_flag=to_int(get("RtkFlag")),
        drone_model=get("DroneModel"),
        camera_serial_number=get("CameraSerialNumber"),
    )
