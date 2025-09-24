"""Utility helpers for Face Sequencer API endpoints."""
from __future__ import annotations

from functools import wraps
from typing import Callable, Optional

from flask import Request, request

from audio_error_handling import (
    validate_audio_file,
)
from audio_exceptions import AlignmentError


def require_audio_upload(field_name: str = "audio") -> Callable:
    """Decorator that validates an uploaded audio file and injects it into the handler."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            file_obj = _get_file_from_request(request, field_name)
            validate_audio_file(file_obj)
            kwargs[field_name] = file_obj
            return func(*args, **kwargs)

        return wrapper

    return decorator


def _get_file_from_request(req: Request, field_name: str):
    file_obj = req.files.get(field_name)
    if not file_obj:
        raise AlignmentError(f"No file provided in field '{field_name}'", details={"field": field_name, 'legacy_error_type': 'upload_error'})
    return file_obj


__all__ = ["require_audio_upload"]
