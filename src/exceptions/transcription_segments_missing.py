class TranscriptionSegmentsMissing(Exception):
    def __init__(self, model: str) -> None:
        super().__init__(
            f"Transcription model {model!r} returned no segments. "
            "Expected verbose_json with timestamp_granularities=['segment']."
        )
