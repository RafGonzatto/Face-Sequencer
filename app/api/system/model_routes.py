"""Model lifecycle endpoints blueprint."""
from __future__ import annotations
from flask import Blueprint, request, jsonify
from app.core.utils.api_responses import success_response, error_response
from app.services.model_manager import get_model_manager, ModelLoadError

model_bp = Blueprint('models', __name__)

@model_bp.route('/api/models/preload', methods=['POST'])
def preload_models():
    data = request.get_json(silent=True) or {}
    requested = data.get('models') or []
    if not isinstance(requested, list) or not requested:
        return jsonify(error_response('No models specified', error_type='validation_error', status=400, details={'expected':'list[str]'})), 400
    mm = get_model_manager()
    for name in list(requested):
        if name not in {m['name'] for m in mm.stats().get('models', [])}:
            alias_type = data.get('register', {}).get(name, {}).get('type') if isinstance(data.get('register'), dict) else None
            if alias_type:
                def _make_loader(t=alias_type):
                    def _loader():
                        if t == 'whisperx_transcribe_tiny':
                            import whisperx_compat as whisperx  # type: ignore
                            import torch  # type: ignore
                            device = 'cuda' if hasattr(torch,'cuda') and torch.cuda.is_available() else 'cpu'
                            return whisperx.load_model('tiny', device, compute_type='int8')
                        raise ModelLoadError(f'Unknown dynamic model type: {t}')
                    return _loader
                mm.register_model(name, _make_loader())
    statuses = mm.preload(requested)
    return jsonify(success_response('Model preload attempted', results=statuses, manager=mm.stats()))

@model_bp.route('/api/models/stats', methods=['GET'])
def model_manager_stats():
    mm = get_model_manager()
    return jsonify(success_response('Model manager stats', manager=mm.stats()))

@model_bp.route('/api/models/list', methods=['GET'])
def model_manager_list():
    mm = get_model_manager()
    stats = mm.stats()
    return jsonify(success_response('Model list', models=stats.get('models', []), loaded=stats.get('loaded_models'), registered=stats.get('registered_models')))

@model_bp.route('/api/models/unload', methods=['POST'])
def model_manager_unload():
    data = request.get_json(silent=True) or {}
    models = data.get('models') or []
    if not isinstance(models, list) or not models:
        return jsonify(error_response('No models specified', error_type='validation_error', status=400, details={'expected':'list[str]'})), 400
    mm = get_model_manager()
    results = {}
    for name in models:
        try:
            results[name] = 'unloaded' if mm.release(name) else 'not_loaded'
        except Exception as e:  # noqa: BLE001
            results[name] = f'error: {e}'
    return jsonify(success_response('Unload attempt completed', results=results, manager=mm.stats()))

__all__ = ['model_bp']
