"""audio_error_adapter.py - Adapter decorator to bridge legacy AudioProcessingError to new hierarchy.

This lightweight decorator lets us progressively migrate code that still raises
`AudioProcessingError` (legacy) by converting those exceptions into the new
`AlignmentError` defined in `audio_exceptions.py`. It can be applied to any
function (including non-Flask helpers) to ensure callers only need to handle
the unified exception types.

Usage:

    from audio_error_adapter import adapt_audio_errors

    @adapt_audio_errors
    def legacy_function(...):
        raise AudioProcessingError(AudioErrorType.ALIGNMENT_FAILED, 'details')

    # Caller will receive AlignmentError instead.

The adapter is idempotent: if the raised exception is already an AlignmentError
it is re-raised directly. Any other unexpected exception type is passed
through (allowing upstream handlers to treat it as unexpected).
"""
from __future__ import annotations

from functools import wraps
from typing import Callable, TypeVar, Any, cast

from audio_exceptions import AlignmentError, map_audio_processing_error

F = TypeVar('F', bound=Callable[..., Any])


def adapt_audio_errors(func: F) -> F:
    """Decorator converting legacy AudioProcessingError -> AlignmentError.

    This should be placed closest to the function raising the errors so that
    upstream layers (API handlers, task runners, etc.) can rely solely on the
    new exception hierarchy.
    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any):  # type: ignore[override]
        try:
            return func(*args, **kwargs)
        except AlignmentError:
            # Already unified – just propagate.
            raise
        except Exception as exc:  # noqa: BLE001 - we intentionally normalize any legacy error here
            mapped = map_audio_processing_error(exc)
            # If mapping produced an AlignmentError (expected path) raise it.
            if isinstance(mapped, AlignmentError):
                raise mapped
            # Otherwise propagate original (should be rare/unexpected).
            raise

    return cast(F, wrapper)

__all__ = ["adapt_audio_errors"]
