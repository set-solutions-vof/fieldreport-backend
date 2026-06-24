from datetime import datetime

from pydantic import BaseModel


class DjiXmpMetadata(BaseModel):
    utc_at_exposure: datetime | None = None
    gps_latitude: float | None = None
    gps_longitude: float | None = None
    absolute_altitude: float | None = None
    relative_altitude: float | None = None
    gimbal_pitch_degree: float | None = None
    gimbal_yaw_degree: float | None = None
    gimbal_roll_degree: float | None = None
    lrf_target_lat: float | None = None
    lrf_target_lon: float | None = None
    lrf_target_alt: float | None = None
    lrf_target_distance: float | None = None
    image_source: str | None = None
    rtk_flag: int | None = None
    drone_model: str | None = None
    camera_serial_number: str | None = None
