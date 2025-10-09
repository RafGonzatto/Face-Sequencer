# error_handlers.py - Unified error handling decorators (WP003)
"""Provide standardized API error handling across modules.

This module introduces a generic @handle_api_errors decorator which:
 - Catches common exception types (ValueError, TimeoutError, FileNotFoundError)
 - Allows raising ClassifiedAPIError for explicit error typing
 - Normalizes responses using api_responses.error_response
 - Supports optional fallback callable
 - Logs errors using the centralized logging system
"""
from __future__ import annotations
from typing import Callable, Optional, Any, Dict
from functools import wraps
import traceback
import inspect

try:
    from flask import jsonify, request
except Exception:  # pragma: no cover - during static analysis without Flask
    jsonify = lambda x: x  # type: ignore
    request = None

from app.core.utils.api_responses import error_response
from app.core.utils.logger import get_logger, log_exception

# Canonical error categories for WP003
VALID_ERROR_TYPES = {
    'validation_error',
    'processing_error',
    'timeout_error',
    'not_found',
    'unexpected_error'
}

class ClassifiedAPIError(Exception):
    def __init__(self, message: str, *, error_type: str = 'processing_error', status: int = 400, details: Optional[Dict[str, Any]] = None):
        if error_type not in VALID_ERROR_TYPES:
            error_type = 'processing_error'
        self.error_type = error_type
        self.status = status
        self.details = details or {}
        super().__init__(message)

    def to_response(self):
        return error_response(
            str(self),
            error_type=self.error_type,
            status=self.status,
            details=self.details
        )

def handle_api_errors(*, fallback: Optional[Callable[[Exception], Any]] = None, logger_name: str = None):
    """Decorator to unify error formatting outside specialized audio pipeline.

    Mapping rules:
      ValueError -> validation_error (400)
      FileNotFoundError -> not_found (404)
      TimeoutError -> timeout_error (504)
      ClassifiedAPIError -> passthrough
      Other -> unexpected_error (500)
    
    Args:
        fallback: Optional function to handle errors in a custom way
        logger_name: Optional name for the logger (defaults to module name)
    """
    def decorator(func: Callable):
        # Get appropriate logger name
        module_name = logger_name or func.__module__
        logger = get_logger(module_name)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Capture request context information when available
            context = {}
            if request:
                try:
                    context.update({
                        'endpoint': request.endpoint,
                        'method': request.method,
                        'path': request.path,
                        'remote_addr': request.remote_addr
                    })
                except Exception:
                    pass
                
            try:
                return func(*args, **kwargs)
            except ClassifiedAPIError as ce:
                # Log the classified error with context
                log_exception(logger, ce, {
                    **context,
                    'error_type': ce.error_type,
                    'status_code': ce.status
                })
                resp = jsonify(ce.to_response())
                try:
                    resp.status_code = ce.status
                except Exception:
                    pass
                return resp
                
            except ValueError as ve:
                # Handle validation errors
                log_exception(logger, ve, {**context, 'error_type': 'validation_error'})
                body = error_response(str(ve), error_type='validation_error', status=400)
                resp = jsonify(body)
                try:
                    resp.status_code = 400
                except Exception:
                    pass
                return resp
                
            except FileNotFoundError as fe:
                # Handle not found errors
                log_exception(logger, fe, {**context, 'error_type': 'not_found'})
                body = error_response(str(fe), error_type='not_found', status=404)
                resp = jsonify(body)
                try:
                    resp.status_code = 404
                except Exception:
                    pass
                return resp
                
            except TimeoutError as te:
                # Handle timeout errors
                log_exception(logger, te, {**context, 'error_type': 'timeout_error'})
                body = error_response(str(te), error_type='timeout_error', status=504)
                resp = jsonify(body)
                try:
                    resp.status_code = 504
                except Exception:
                    pass
                return resp
                
            except Exception as e:  # noqa: BLE001
                # Try custom fallback handler if provided
                if fallback:
                    try:
                        logger.info(f"Trying fallback handler for {e.__class__.__name__}")
                        return fallback(e, *args, **kwargs)
                    except Exception as fb_err:  # noqa: BLE001
                        log_exception(logger, fb_err, {**context, 'phase': 'fallback_handler'})
                
                # Log unexpected errors with full context
                log_exception(logger, e, {**context, 'error_type': 'unexpected_error'})
                
                body = error_response(
                    'An unexpected error occurred',
                    error_type='unexpected_error',
                    status=500,
                    details={'error': str(e)}
                )
                resp = jsonify(body)
                try:
                    resp.status_code = 500
                except Exception:
                    pass
                return resp
        return wrapper
    return decorator

__all__ = [
    'handle_api_errors',
    'ClassifiedAPIError',
]
