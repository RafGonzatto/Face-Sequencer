"""Audio-related API endpoints blueprint.

Contains upload, markers, and future audio analysis endpoints.
"""
from __future__ import annotations
from flask import Blueprint, request, jsonify
from api_responses import error_response, success_response
from logger import get_logger

audio_bp = Blueprint('audio', __name__)
logger = get_logger(__name__)

# NOTE: /api/audio/upload endpoint is implemented in app.py 
# to avoid route conflicts and ensure proper file handling

@audio_bp.route('/api/audio/markers', methods=['POST'])
def get_audio_markers():  # mirrored from app.py
    data = request.get_json()
    if not data:
        return jsonify(error_response('No data provided', error_type='validation_error', status=400)), 400
    alignment = data.get('alignment')
    if not alignment:
        return jsonify(error_response('No alignment provided', error_type='validation_error', status=400)), 400
    tokens = alignment.get('tokens', [])
    audio_duration_ms = alignment.get('audio', {}).get('duration_ms', 3000)
    word_tokens = [t for t in tokens if t.get('type') == 'word']
    markers = []
    for token in word_tokens:
        start_ms = token.get('start_ms', 0)
        position_percent = (start_ms / audio_duration_ms) * 100 if audio_duration_ms > 0 else 0
        markers.append({'text': token.get('text', ''), 'position': position_percent, 'time_ms': start_ms})
    return jsonify(success_response('Markers computed', markers=markers))

__all__ = ['audio_bp']
