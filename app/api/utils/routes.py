"""Utility / demo endpoints blueprint.

Isolates lightweight utility routes from early import-time side-effects in
``app.py``.

The current error demo endpoint (``/api/util/error-demo-v2``) demonstrates the
standardized error response contract. The legacy ``/api/util/error-demo`` route
was removed after migration – keeping only a single canonical endpoint reduces
confusion and simplifies tests.
"""
from __future__ import annotations
from flask import Blueprint, request, jsonify
from app.core.utils.api_responses import error_response, success_response
import os

util_bp = Blueprint('util', __name__)

@util_bp.route('/api/util/error-demo-v2', methods=['GET'])
def util_error_demo_v2():  # pragma: no cover (covered indirectly in tests)
    mode = (request.args.get('mode', 'ok') or 'ok').strip().lower()
    try:
        os.environ['UTIL_ERROR_DEMO_V2_LAST_MODE'] = mode
    except Exception:
        pass

    def _err(msg: str, et: str, status: int):
        body = error_response(msg, error_type=et, status=status)
        body['lifecycle_stage'] = 'general'
        resp = jsonify(body)
        resp.status_code = status
        return resp

    if mode == 'value':
        return _err('Simulated validation error', 'validation_error', 400)
    if mode == 'missing':
        return _err('Simulated not found', 'not_found', 404)
    if mode == 'timeout':
        return _err('Simulated timeout', 'timeout_error', 504)
    if mode == 'classified':
        return _err('Explicit processing classification', 'processing_error', 422)
    ok_body = success_response('OK', mode=mode)
    return jsonify(ok_body), 200

# Backward compatibility: legacy endpoint expected by older tests
@util_bp.route('/api/util/error-demo', methods=['GET'])
def util_error_demo_legacy():  # pragma: no cover - thin wrapper
    # Delegate to the v2 logic without forcing clients to upgrade immediately
    return util_error_demo_v2()

__all__ = [
    'util_bp',
]
