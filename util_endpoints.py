"""Utility / demo endpoints blueprint.

This isolates utility routes from early import-time side-effects in app.py.

The v2 error demo endpoint demonstrates standardized error response contracts
without relying on decorator mutation. A legacy /api/util/error-demo route is
retained and delegates to the v2 implementation for backward compatibility.
"""
from __future__ import annotations
from flask import Blueprint, request, jsonify
from api_responses import error_response, success_response
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

@util_bp.route('/api/util/error-demo', methods=['GET'])
def util_error_demo_legacy():  # pragma: no cover - thin delegate
    # Backward compatibility: delegate to v2 behavior
    return util_error_demo_v2()

__all__ = [
    'util_bp',
]
