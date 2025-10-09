"""audio_exceptions.py - Unified audio/model exception hierarchy (WP004)

This file defines a structured exception hierarchy used across audio
alignment and model lifecycle code. It complements the pre-existing
`audio_error_handling` module but provides more granular semantic
categories and a base class that captures context.

Hierarchy:
  FaceSequencerError (base)
    ModelError
      ModelLoadError
      ModelNotFoundError
      ModelMemoryError
    AudioError
      AlignmentError
      AudioProcessingErrorLegacy (bridge to existing AudioProcessingError)

Each error can expose recommendations for user-facing responses.
"""
from __future__ import annotations
from typing import Dict, Any, List, Optional

__all__ = [
    'FaceSequencerError', 'ModelError', 'ModelLoadError', 'ModelNotFoundError',
    'ModelMemoryError', 'AudioError', 'AlignmentError', 'map_audio_processing_error'
]


class FaceSequencerError(Exception):
    category = 'general_error'
    default_message = 'An unexpected error occurred'
    recommendations: List[str] = []

    def __init__(self, message: Optional[str] = None, *, details: Optional[Dict[str, Any]] = None):
        super().__init__(message or self.default_message)
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            'error_type': self.category,
            'error': str(self),
            'details': self.details,
            'recommendations': self.recommendations,
        }


class ModelError(FaceSequencerError):
    category = 'model_error'
    default_message = 'Model error'


class ModelLoadError(ModelError):
    category = 'model_load_error'
    default_message = 'Failed to load model'
    recommendations = [
        'Verify model files are accessible',
        'Check available GPU/CPU memory',
        'Try preloading the model earlier in the workflow'
    ]


class ModelNotFoundError(ModelError):
    category = 'model_not_found'
    default_message = 'Requested model is not registered'
    recommendations = [
        'Call /api/models/preload with the model name',
        'Verify the model identifier is correct'
    ]


class ModelMemoryError(ModelError):
    category = 'model_memory_limit'
    default_message = 'Model memory budget exceeded'
    recommendations = [
        'Increase FACE_SEQ_MODEL_MAX_MEMORY_MB',
        'Unload unused models via manager.release(name)',
        'Reduce concurrent large model usage'
    ]


class AudioError(FaceSequencerError):
    category = 'audio_error'


class AlignmentError(AudioError):
    category = 'alignment_error'
    default_message = 'Audio alignment failed'
    recommendations = [
        'Confirm transcript matches spoken audio',
        'Use clearer audio with less background noise',
        'Try shorter segments or fallback to manual timing'
    ]


def map_audio_processing_error(exc) -> AlignmentError:
    """Bridge existing AudioProcessingError -> AlignmentError for unified responses."""
    try:
        from app.services.audio_error_handling import AudioProcessingError, AudioErrorType  # type: ignore
        if isinstance(exc, AudioProcessingError):  # legacy -> new
            details = getattr(exc, 'details', {}) or {}
            return AlignmentError(str(exc), details=details)
    except Exception:
        pass
    if isinstance(exc, AlignmentError):
        return exc
    return AlignmentError(str(exc))
