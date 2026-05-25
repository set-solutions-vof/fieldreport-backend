from pydantic import BaseModel


class AudioChunk(BaseModel):
    filename: str
    content: bytes
    duration_seconds: float


class ChunkTranscription(BaseModel):
    text: str
    duration_seconds: float


class TranscriptionSegment(BaseModel):
    segment_index: int
    start_seconds: float
    end_seconds: float
    text: str


class TranscriptionResult(BaseModel):
    full_text: str
    duration_seconds: float
    segments: list[TranscriptionSegment]
