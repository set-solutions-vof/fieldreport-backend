from src.utils.dji_xmp import extract_dji_xmp

_DJI_NS = "http://www.dji.com/drone-dji/1.0/"

_FULL_XMP = b"""
<x:xmpmeta xmlns:x='adobe:ns:meta/' xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#'
            xmlns:drone-dji='http://www.dji.com/drone-dji/1.0/'>
  <rdf:RDF>
    <rdf:Description rdf:about=''
      drone-dji:UTCAtExposure='2024-05-01T10:30:00Z'
      drone-dji:GpsLatitude='52.123456'
      drone-dji:GpsLongitude='4.654321'
      drone-dji:AbsoluteAltitude='120.5'
      drone-dji:RelativeAltitude='80.0'
      drone-dji:GimbalPitchDegree='-45.0'
      drone-dji:GimbalYawDegree='90.0'
      drone-dji:GimbalRollDegree='0.0'
      drone-dji:LRFTargetLat='52.124000'
      drone-dji:LRFTargetLon='4.655000'
      drone-dji:LRFTargetAlt='5.0'
      drone-dji:LRFTargetDistance='120.3'
      drone-dji:ImageSource='InfraredCamera'
      drone-dji:RtkFlag='50'
      drone-dji:DroneModel='Matrice 4T'
      drone-dji:CameraSerialNumber='SN12345'
    />
  </rdf:RDF>
</x:xmpmeta>
""".strip()


def test_extract_dji_xmp_parses_all_fields() -> None:
    content = b"JUNK_JPEG_BYTES" + _FULL_XMP + b"MORE_JUNK"

    meta = extract_dji_xmp(content)

    assert meta is not None
    assert meta.gps_latitude == 52.123456
    assert meta.gps_longitude == 4.654321
    assert meta.absolute_altitude == 120.5
    assert meta.relative_altitude == 80.0
    assert meta.gimbal_pitch_degree == -45.0
    assert meta.gimbal_yaw_degree == 90.0
    assert meta.gimbal_roll_degree == 0.0
    assert meta.lrf_target_lat == 52.124000
    assert meta.lrf_target_lon == 4.655000
    assert meta.lrf_target_alt == 5.0
    assert meta.lrf_target_distance == 120.3
    assert meta.image_source == "InfraredCamera"
    assert meta.rtk_flag == 50
    assert meta.drone_model == "Matrice 4T"
    assert meta.camera_serial_number == "SN12345"
    assert meta.utc_at_exposure is not None
    assert meta.utc_at_exposure.year == 2024


def test_extract_dji_xmp_returns_none_when_no_xmp_block() -> None:
    assert extract_dji_xmp(b"plain jpeg bytes with no xmp") is None


def test_extract_dji_xmp_handles_partial_fields() -> None:
    partial_xmp = (
        b"<x:xmpmeta xmlns:x='adobe:ns:meta/' xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#'"
        b" xmlns:drone-dji='http://www.dji.com/drone-dji/1.0/'>"
        b"<rdf:RDF><rdf:Description rdf:about=''"
        b" drone-dji:GpsLatitude='51.5' drone-dji:GpsLongitude='3.2'/>"
        b"</rdf:RDF></x:xmpmeta>"
    )

    meta = extract_dji_xmp(partial_xmp)

    assert meta is not None
    assert meta.gps_latitude == 51.5
    assert meta.gps_longitude == 3.2
    assert meta.image_source is None
    assert meta.drone_model is None
    assert meta.lrf_target_lat is None
    assert meta.utc_at_exposure is None
