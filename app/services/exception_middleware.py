# exception_middleware.py - Global exception handling middleware
"""
Provides application-wide error handling for Flask applications.
This middleware catches uncaught exceptions and formats them into standard error responses.
"""

from typing import Any, Tuple, Dict, Optional
from flask import Flask, request, jsonify, Response

from app.core.utils.logger import get_logger, log_exception
from app.core.utils.api_responses import error_response

# Get logger for this module
middleware_logger = get_logger('middleware')

def register_exception_handlers(app: Flask) -> None:
    """
    Register global exception handlers for a Flask application.
    
    Args:
        app: Flask application instance
    """
    # Handle generic exceptions
    @app.errorhandler(Exception)
    def handle_exception(e: Exception) -> Tuple[Response, int]:
        """Handle uncaught exceptions globally"""
        # Build context for logging
        context = {
            'endpoint': request.endpoint,
            'method': request.method,
            'path': request.path,
            'remote_addr': request.remote_addr
        }
        
        # Log the exception with context
        log_exception(middleware_logger, e, context)
        
        # Return standardized error response
        response = error_response(
            "An unexpected error occurred",
            error_type='unexpected_error',
            status=500,
            details={'error': str(e)}
        )
        return jsonify(response), 500
    
    # Handle 404 Not Found errors
    @app.errorhandler(404)
    def handle_not_found(e: Exception) -> Tuple[Response, int]:
        """Handle 404 errors"""
        context = {
            'endpoint': request.endpoint,
            'method': request.method,
            'path': request.path,
            'remote_addr': request.remote_addr
        }
        middleware_logger.warning(f"404 Not Found: {request.path}", extra=context)
        
        response = error_response(
            f"Resource not found: {request.path}",
            error_type='not_found',
            status=404
        )
        return jsonify(response), 404
    
    # Handle 405 Method Not Allowed
    @app.errorhandler(405)
    def handle_method_not_allowed(e: Exception) -> Tuple[Response, int]:
        """Handle 405 errors"""
        context = {
            'endpoint': request.endpoint,
            'method': request.method,
            'path': request.path,
            'remote_addr': request.remote_addr
        }
        middleware_logger.warning(f"405 Method Not Allowed: {request.method} {request.path}", extra=context)
        
        response = error_response(
            f"Method {request.method} not allowed for {request.path}",
            error_type='validation_error',
            status=405
        )
        return jsonify(response), 405
    
    # Handle 400 Bad Request
    @app.errorhandler(400)
    def handle_bad_request(e: Exception) -> Tuple[Response, int]:
        """Handle 400 errors"""
        context = {
            'endpoint': request.endpoint,
            'method': request.method,
            'path': request.path,
            'remote_addr': request.remote_addr
        }
        middleware_logger.warning(f"400 Bad Request: {request.path}", extra=context)
        
        response = error_response(
            "Bad request",
            error_type='validation_error',
            status=400,
            details={'error': str(e)}
        )
        return jsonify(response), 400
        
    # Handle 500 Internal Server Error
    @app.errorhandler(500)
    def handle_server_error(e: Exception) -> Tuple[Response, int]:
        """Handle 500 errors"""
        context = {
            'endpoint': request.endpoint,
            'method': request.method,
            'path': request.path,
            'remote_addr': request.remote_addr
        }
        log_exception(middleware_logger, e, context)
        
        response = error_response(
            "Internal server error",
            error_type='unexpected_error',
            status=500,
            details={'error': str(e)}
        )
        return jsonify(response), 500

def configure_app_error_handling(app: Flask) -> None:
    """
    Configure a Flask app with comprehensive error handling
    
    Args:
        app: Flask application instance
    """
    # Register exception handlers
    register_exception_handlers(app)
    
    # Log application startup
    middleware_logger.info(f"Configured error handling middleware for Flask application")