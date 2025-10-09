"""Alignment & audio upload endpoints (refatorado limpo).

Fornece:
  - GET /api/audio/status
  - POST /api/audio/upload (multipart campo 'audio')
  - POST /api/audio/align { filename, text, language? }
  - POST /api/audio/align-enhanced (fallback para standard se pipeline enhanced indisponível)
"""
from __future__ import annotations
import os, time, hashlib
from flask import Blueprint, jsonify, request, current_app
from werkzeug.utils import secure_filename

from app.core.utils.api_responses import success_response, error_response
from app.core.audio.audio_aligner import AudioAligner
from app.core.audio.audio_factory import ComponentFactory

audio_align_bp = Blueprint("audio_align", __name__)

_aligner_instance: AudioAligner | None = None

def _get_aligner(enhanced: bool = True) -> AudioAligner:
    global _aligner_instance
    if _aligner_instance is None:
        factory = ComponentFactory()
        _aligner_instance = AudioAligner(factory=factory, auto_build_enhanced=enhanced)
    return _aligner_instance

def _audio_folder() -> str:
    folder = current_app.config.get("AUDIO_FOLDER") or os.path.join(current_app.root_path, "..", "uploads", "audio")
    os.makedirs(folder, exist_ok=True)
    return folder

@audio_align_bp.route("/api/audio/status", methods=["GET"])
def audio_status():
    try:
        aligner = _get_aligner(enhanced=True)
        return jsonify(success_response(
            "Audio alignment system status",
            available=True,
            enhanced_available=bool(aligner.use_enhanced),
            language=aligner.language,
            features={
                "basic_alignment": True,
                "enhanced_pipeline": bool(aligner.use_enhanced),
            }
        ))
    except Exception as e:  # noqa: BLE001
        return jsonify(success_response(
            "Audio alignment degraded",
            available=False,
            enhanced_available=False,
            error=str(e)
        ))

@audio_align_bp.route("/api/audio/files", methods=["GET"])
def list_audio_files():
    """List uploaded audio files (debug helper).

    Optional query params:
      - limit: int (default 50)
      - latest: bool (if true returns only the most recent file)
    """
    folder = _audio_folder()
    try:
        entries = []
        for name in os.listdir(folder):
            path = os.path.join(folder, name)
            if os.path.isfile(path):
                stat = os.stat(path)
                entries.append({
                    'filename': name,
                    'size': stat.st_size,
                    'mtime': stat.st_mtime,
                })
        # Sort newest first
        entries.sort(key=lambda x: x['mtime'], reverse=True)
        latest = request.args.get('latest')
        if latest and latest.lower() in {"1", "true", "yes"}:
            entries = entries[:1]
        try:
            limit = int(request.args.get('limit', '50'))
        except ValueError:
            limit = 50
        return jsonify(success_response('Audio files', files=entries[:limit]))
    except FileNotFoundError:
        return jsonify(success_response('Audio files', files=[]))

@audio_align_bp.route("/api/audio/upload", methods=["POST"])
def upload_audio():
    if 'audio' not in request.files:
        return jsonify(error_response('Missing file field: audio', error_type='validation_error', status=400)), 400
    file = request.files['audio']
    if not file.filename:
        return jsonify(error_response('Empty filename', error_type='validation_error', status=400)), 400
    folder = _audio_folder()
    ts = int(time.time())
    safe_name = secure_filename(file.filename)
    filename = f"{ts}_{safe_name}"
    path = os.path.join(folder, filename)
    file.save(path)
    file_hash = hashlib.sha1(open(path, 'rb').read()).hexdigest()
    return jsonify(success_response('Audio uploaded', filename=filename, size=os.path.getsize(path), file_hash=file_hash))

def _normalize_tokens(tokens):
    norm = []
    for t in tokens:
        d = {
            'type': getattr(t, 'type', None).value if getattr(t, 'type', None) else 'word',
            'text': getattr(t, 'text', ''),
            'start_ms': getattr(t, 'start_ms', 0),
            'end_ms': getattr(t, 'end_ms', 0),
            'confidence': getattr(t, 'confidence', 0.0),
            'lang': getattr(t, 'lang', ''),
        }
        d['duration_ms'] = d['end_ms'] - d['start_ms']
        norm.append(d)
    return norm

def _build_payload(result, tokens_norm, method: str):
    return {
        'success': True,
        'alignment': {
            'language': result.language,
            'sample_rate': result.sample_rate,
            'tokens': tokens_norm,
            'stats': {
                'audio_ms': result.stats.audio_ms,
                'avg_confidence': result.stats.avg_confidence,
            },
            'method': method,
        },
        'sequence': tokens_norm,
        'stats': {
            'total_tokens': len(tokens_norm),
            'word_tokens': sum(1 for t in tokens_norm if t['type'] == 'word'),
            'total_duration_ms': result.stats.audio_ms,
            'method': method,
        },
        'cached': False,
        'message': 'Audio alignment completed successfully',
    }

@audio_align_bp.route("/api/audio/align", methods=["POST"])
def align_audio_basic():
    data = request.get_json() or {}
    filename = data.get('filename')
    text = (data.get('text') or '').strip()
    language = data.get('language') or 'pt-BR'
    if not filename or not text:
        return jsonify(error_response('Missing filename or text', error_type='validation_error', status=400)), 400
    folder = _audio_folder()
    audio_path = os.path.join(folder, filename)
    if not os.path.exists(audio_path):
        return jsonify(error_response('Audio file not found', error_type='not_found', status=404)), 404
    try:
        aligner = _get_aligner(enhanced=True)
        result = aligner.align_audio_to_text(audio_path, text, language=language)
        tokens_norm = _normalize_tokens(result.tokens)
        payload = _build_payload(result, tokens_norm, method='standard')
        return jsonify(payload)
    except Exception as e:  # noqa: BLE001
        return jsonify(error_response(str(e), error_type='alignment_error', status=500)), 500

@audio_align_bp.route("/api/audio/align-enhanced", methods=["POST"])
def align_audio_enhanced():
    data = request.get_json() or {}
    filename = data.get('filename')
    text = (data.get('text') or '').strip()
    language = data.get('language') or 'pt-BR'
    if not filename or not text:
        return jsonify(error_response('Missing filename or text', error_type='validation_error', status=400)), 400
    folder = _audio_folder()
    audio_path = os.path.join(folder, filename)
    if not os.path.exists(audio_path):
        return jsonify(error_response('Audio file not found', error_type='not_found', status=404)), 404
    try:
        aligner = _get_aligner(enhanced=True)
        if not aligner.use_enhanced:
            # fallback to standard
            result = aligner.align_audio_to_text(audio_path, text, language=language)
            tokens_norm = _normalize_tokens(result.tokens)
            return jsonify(_build_payload(result, tokens_norm, method='standard_fallback'))
        # Enhanced path uses internal composite method
        enhanced_method = getattr(aligner, 'align_audio_to_text_enhanced', None)
        if not enhanced_method:
            result = aligner.align_audio_to_text(audio_path, text, language=language)
            tokens_norm = _normalize_tokens(result.tokens)
            return jsonify(_build_payload(result, tokens_norm, method='standard_fallback'))
        result_enhanced, timeline, frame_states = enhanced_method(audio_path, text, language=language)
        tokens_norm = _normalize_tokens(result_enhanced.tokens)
        payload = _build_payload(result_enhanced, tokens_norm, method='enhanced')
        payload['alignment']['timeline'] = [
            {
                'word': getattr(wt, 'word', ''),
                'start_time': getattr(wt, 'start_time', 0),
                'end_time': getattr(wt, 'end_time', 0),
                'start_frame': getattr(wt, 'start_frame', 0),
                'end_frame': getattr(wt, 'end_frame', 0),
                'confidence': getattr(wt, 'confidence', 0.0),
            } for wt in (timeline or [])
        ]
        payload['alignment']['frame_states'] = [
            {
                'frame_number': getattr(fs, 'frame_number', 0),
                'timestamp': getattr(fs, 'timestamp', 0),
                'active_word': getattr(fs, 'active_word', ''),
                'viseme': getattr(fs, 'viseme', ''),
                'confidence': getattr(fs, 'confidence', 0.0),
            } for fs in (frame_states or [])
        ]
        return jsonify(payload)
    except Exception as e:  # noqa: BLE001
        return jsonify(error_response(str(e), error_type='alignment_error', status=500)), 500

__all__ = ["audio_align_bp"]
