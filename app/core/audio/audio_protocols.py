"""audio_protocols.py

Protocol (interface) definitions for audio processing components.
Part of WP001 Dependency Injection Refactor.

These Protocols allow the high-level `AudioAligner` to depend only on
abstractions, enabling test doubles and alternative implementations
without modifying the aligner itself.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable, List, Optional, Any, Tuple
import numpy as np

# NOTE: We intentionally avoid importing heavy implementation modules here
# to prevent circular imports and unnecessary model downloads.

@runtime_checkable
class SilenceDetectorProtocol(Protocol):
    """Detects silence (pauses) in an audio signal.

    Expected to return a list of silence segment objects. Implementations
    may return custom dataclasses; only the attributes `start_time`,
    `end_time`, and `confidence` (float seconds + confidence score) are
    accessed by the rest of the pipeline.
    """
    def detect_silence_segments(
        self,
        audio_data: np.ndarray,
        adaptive_thresholds: bool = True,
        **kwargs: Any
    ) -> List[Any]:
        ...

@runtime_checkable
class ForcedAlignerProtocol(Protocol):
    """Performs forced alignment of text to audio.

    Returns an alignment result object with at minimum:
      - tokens: iterable of objects each having (text, start_time, end_time, confidence)
      - total_duration: float (seconds)
    Additional fields are allowed and ignored by the consumer.
    """
    def align_text_to_audio(
        self,
        audio: np.ndarray,
        text: str,
        sample_rate: int = 16000,
        method: str = "auto"
    ) -> Any:  # Using Any to decouple from concrete dataclasses
        ...

@runtime_checkable
class FrameSynchronizerProtocol(Protocol):
    """Builds frame-precise animation timelines and frame state sequences."""

    fps: float  # Implementations expose current frames-per-second

    def create_animation_timeline(
        self,
        word_timings: List[Tuple[str, float, float]],
        total_duration: float,
        confidence_scores: Optional[List[float]] = None,
        silence_segments: Optional[List[Any]] = None
    ) -> List[Any]:  # List of WordTiming-like objects
        ...

    def optimize_timeline(self, timeline: List[Any]) -> List[Any]:
        ...

    def generate_frame_sequence(
        self,
        timeline: List[Any],
        total_duration: float,
        frame_step: int = 1
    ) -> List[Any]:  # List of FrameState-like objects
        ...

__all__ = [
    "SilenceDetectorProtocol",
    "ForcedAlignerProtocol",
    "FrameSynchronizerProtocol",
]
