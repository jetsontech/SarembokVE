"""Provider-neutral Sarembok voice/audio architecture.

Defines streaming audio chunks, speech events, interruption (barge-in), and
adapter contracts for speech recognition and synthesis. Vendor implementations
remain outside the core contract.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional, Protocol


class AudioEventType(str, Enum):
    AUDIO_START = "audio.start"
    AUDIO_CHUNK = "audio.chunk"
    AUDIO_END = "audio.end"
    TRANSCRIPT_PARTIAL = "transcript.partial"
    TRANSCRIPT_FINAL = "transcript.final"
    SPEECH_START = "speech.start"
    SPEECH_END = "speech.end"
    INTERRUPT = "speech.interrupt"


@dataclass(frozen=True)
class AudioFormat:
    sample_rate_hz: int = 16000
    channels: int = 1
    encoding: str = "pcm_s16le"


@dataclass(frozen=True)
class AudioChunk:
    stream_id: str
    sequence: int
    payload_ref: str
    format: AudioFormat = field(default_factory=AudioFormat)


@dataclass(frozen=True)
class SpeechEvent:
    event_type: AudioEventType
    stream_id: str
    text: Optional[str] = None
    confidence: Optional[float] = None
    sequence: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class SpeechRecognizer(Protocol):
    def accept_audio(self, chunk: AudioChunk) -> list[SpeechEvent]: ...
    def end_stream(self, stream_id: str) -> list[SpeechEvent]: ...


class SpeechSynthesizer(Protocol):
    def synthesize(self, text: str, stream_id: str) -> list[AudioChunk]: ...


class VoiceSession:
    """Coordinates speech events while allowing user interruption."""

    def __init__(self, recognizer: SpeechRecognizer, synthesizer: SpeechSynthesizer):
        self.recognizer = recognizer
        self.synthesizer = synthesizer
        self.output_interrupted = False

    def ingest(self, chunk: AudioChunk) -> list[SpeechEvent]:
        return self.recognizer.accept_audio(chunk)

    def interrupt(self, stream_id: str) -> SpeechEvent:
        self.output_interrupted = True
        return SpeechEvent(AudioEventType.INTERRUPT, stream_id)

    def speak(self, text: str, stream_id: str) -> list[AudioChunk]:
        self.output_interrupted = False
        return self.synthesizer.synthesize(text, stream_id)
