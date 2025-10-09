"""Sequence management endpoints blueprint."""
from __future__ import annotations
from flask import Blueprint, jsonify, request
from app.core.utils.api_responses import success_response, error_response
from lipanim_core_demo import valid_img
import base64, io
from PIL import Image

sequence_bp = Blueprint('sequence', __name__)

def _state(app):
    return app.config['app_state']

@sequence_bp.route('/api/sequence/frame/<int:frame_id>', methods=['GET'])
def get_frame_image(frame_id):
    from flask import current_app
    try:
        sequence = _state(current_app)['current_project']['sequence']
        if frame_id < 0 or frame_id >= len(sequence):
            return jsonify(error_response('Frame not found', error_type='not_found', status=404)), 404
        frame = sequence[frame_id]
        if frame.get('img') is None:
            return jsonify(success_response('Pause frame', is_pause=True, char=frame.get('char'), duration=frame.get('ms')))
        # Resolve mapping entries that might be dicts
        img_ref = frame.get('img')
        if isinstance(img_ref, dict):
            img_ref = img_ref.get('abs_path') or img_ref.get('path')
        if not valid_img(img_ref):
            # Try fallback_img if present
            fb = frame.get('fallback_img')
            if isinstance(fb, dict):
                fb = fb.get('abs_path') or fb.get('path')
            if not valid_img(fb):
                return jsonify(error_response('Image not found', error_type='not_found', status=404)), 404
            img_ref = fb
        with Image.open(img_ref) as img:
            if max(img.size) > 800:
                img.thumbnail((800, 800), Image.Resampling.LANCZOS)
            buffer = io.BytesIO(); img.save(buffer, format='PNG')
            image_data = base64.b64encode(buffer.getvalue()).decode()
            dims = img.size
        return jsonify(success_response('Frame retrieved', is_pause=False, char=frame.get('char'), duration=frame.get('ms'), image=f"data:image/png;base64,{image_data}", dimensions=dims))
    except Exception as e:  # noqa: BLE001
        return jsonify(error_response(str(e), error_type='unexpected_error', status=500)), 500

@sequence_bp.route('/api/sequence/update', methods=['POST'])
def update_sequence():
    from flask import current_app
    try:
        data = request.get_json() or {}
        frame_id = data.get('frame_id')
        updates = data.get('updates', {})
        sequence = _state(current_app)['current_project']['sequence']
        if frame_id < 0 or frame_id >= len(sequence):
            return jsonify(error_response('Invalid frame ID', error_type='validation_error', status=400)), 400
        if 'duration' in updates:
            sequence[frame_id]['ms'] = max(1, int(updates['duration']))
        return jsonify(success_response('Frame updated'))
    except Exception as e:  # noqa: BLE001
        return jsonify(error_response(str(e), error_type='unexpected_error', status=400)), 400

@sequence_bp.route('/api/sequence/reorder', methods=['POST'])
def reorder_sequence():
    from flask import current_app
    try:
        data = request.get_json() or {}
        from_index = data.get('from_index')
        to_index = data.get('to_index')
        sequence = _state(current_app)['current_project']['sequence']
        if (from_index < 0 or from_index >= len(sequence) or to_index < 0 or to_index >= len(sequence)):
            return jsonify(error_response('Invalid frame indices', error_type='validation_error', status=400)), 400
        frame = sequence.pop(from_index); sequence.insert(to_index, frame)
        return jsonify(success_response('Sequence reordered'))
    except Exception as e:  # noqa: BLE001
        return jsonify(error_response(str(e), error_type='unexpected_error', status=400)), 400

@sequence_bp.route('/api/sequence/delete', methods=['POST'])
def delete_frame():
    from flask import current_app
    try:
        data = request.get_json() or {}
        frame_id = data.get('frame_id')
        sequence = _state(current_app)['current_project']['sequence']
        if frame_id < 0 or frame_id >= len(sequence):
            return jsonify(error_response('Invalid frame ID', error_type='validation_error', status=400)), 400
        del sequence[frame_id]
        return jsonify(success_response('Frame deleted'))
    except Exception as e:  # noqa: BLE001
        return jsonify(error_response(str(e), error_type='unexpected_error', status=400)), 400

__all__ = ['sequence_bp']
