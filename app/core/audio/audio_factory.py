"""audio_factory.py

Factory for constructing audio processing component instances.
Part of WP001 Dependency Injection Refactor.

Centralizes creation to avoid scattered imports and heavy model loads.
Consumers (e.g. `AudioAligner`) can request components through this
factory or inject test doubles directly.
"""
from __future__ import annotations

from typing import Optional

from app.core.audio.audio_protocols import (
    SilenceDetectorProtocol,
    ForcedAlignerProtocol,
    FrameSynchronizerProtocol,
)

class ComponentFactory:
    """Factory responsible for instantiating concrete component implementations.

    Lazily imports heavy modules only when first requested to minimize
    startup cost and reduce circular import risk.
    """

    def __init__(self, device: str = "auto", language: str = "pt-BR"):
        self.device = device
        self.language = language
        self._silence_detector: Optional[SilenceDetectorProtocol] = None
        self._forced_aligner: Optional[ForcedAlignerProtocol] = None
        self._frame_synchronizer: Optional[FrameSynchronizerProtocol] = None

    def silence_detector(self) -> SilenceDetectorProtocol:
        if self._silence_detector is None:
            from app.core.audio.enhanced_silence_detector import EnhancedSilenceDetector
            from app.core.utils.config import config
            self._silence_detector = EnhancedSilenceDetector(
                sample_rate=config.audio.sample_rate()
            )
        return self._silence_detector

    def forced_aligner(self) -> ForcedAlignerProtocol:
        if self._forced_aligner is None:
            from app.core.audio.forced_alignment import ForcedAligner
            # ForcedAligner expects two-letter language code sometimes
            lang_code = (self.language or "pt")[:2]
            self._forced_aligner = ForcedAligner(device=self.device, language=lang_code)
        return self._forced_aligner

    def frame_synchronizer(self) -> FrameSynchronizerProtocol:
        if self._frame_synchronizer is None:
            from app.core.export.frame_synchronizer import PreciseFrameSynchronizer
            from app.core.utils.config import config
            fps = float(config.project_defaults.fps())
            self._frame_synchronizer = PreciseFrameSynchronizer(fps=fps)
        return self._frame_synchronizer

    # Convenience method to build the full enhanced stack
    def build_enhanced_stack(self):
        return (
            self.silence_detector(),
            self.forced_aligner(),
            self.frame_synchronizer(),
        )

__all__ = ["ComponentFactory"]
