"""Standard API response formatting and error schema utilities."""
from __future__ import annotations
from typing import Any, Dict, Optional


def success_response(message: str = "OK", **payload) -> Dict[str, Any]:
    return {
        "success": True,
        "message": message,
        **payload,
    }


def error_response(error: str, *, error_type: Optional[str] = None, status: int = 400, details: Optional[Dict[str, Any]] = None, recommendations: Optional[list] = None, lifecycle: Optional[str] = None) -> Dict[str, Any]:
    body = {
        "success": False,
        "error": error,
        "status": status,
    }
    if error_type:
        body["error_type"] = error_type
    if details:
        body["details"] = details
    if recommendations:
        body["recommendations"] = recommendations
    if lifecycle:  # where in the pipeline the error originated (e.g. 'preload','alignment','export')
        body["lifecycle_stage"] = lifecycle
    return body


__all__ = ["success_response", "error_response"]
