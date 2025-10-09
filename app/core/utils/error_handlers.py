"""
Funções para tratamento de erros da aplicação
"""
from flask import Flask, jsonify, request
from app.core.utils.api_responses import error_response

def register_error_handlers(app: Flask):
    """
    Registra tratadores de erro para a aplicação Flask
    """
    @app.errorhandler(400)
    def bad_request(e):
        return error_response("Bad request", status_code=400)

    @app.errorhandler(404)
    def not_found(e):
        return error_response("Resource not found", status_code=404)

    @app.errorhandler(500)
    def server_error(e):
        return error_response("Internal server error", status_code=500)

    @app.errorhandler(Exception)
    def handle_exception(e):
        # Log the exception
        app.logger.error(f"Unhandled exception: {str(e)}")
        return error_response("Internal server error", status_code=500)