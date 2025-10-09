"""System / metrics / cache endpoints blueprint."""
from __future__ import annotations
from flask import Blueprint, jsonify
from app.core.utils.api_responses import success_response, error_response

system_bp = Blueprint('system', __name__)

def _state(app):
    return app.config['app_state']

@system_bp.route('/api/cache/stats', methods=['GET'])
def cache_stats_endpoint():
    from flask import current_app
    try:
        audio_cache = current_app.config['audio_cache']
        stats = audio_cache.stats()
        from app.core.utils.metrics import metrics_snapshot
        return jsonify(success_response('Audio cache statistics', data=stats, metrics=metrics_snapshot()))
    except Exception as e:  # noqa: BLE001
        return jsonify(error_response(str(e), error_type='unexpected_error', status=500)), 500

@system_bp.route('/api/health', methods=['GET'])
def health_check():
    from flask import current_app
    try:
        app_state = _state(current_app)
        from app import AUDIO_ALIGNMENT_AVAILABLE, ENHANCED_ALIGNMENT_AVAILABLE  # circular safe: constants
        audio_cache = current_app.config['audio_cache']
        from app.core.utils.metrics import metrics_snapshot
        components = {
            'audio_alignment': AUDIO_ALIGNMENT_AVAILABLE,
            'enhanced_alignment': ENHANCED_ALIGNMENT_AVAILABLE,
            'cache_entries': audio_cache.stats().get('entries'),
            'export_tasks_active': sum(1 for t in app_state['export_tasks'].values() if t['status'] in {'pending','processing'}),
        }
        cache_stats_local = audio_cache.stats()
        health = success_response(
            'Health check OK' if AUDIO_ALIGNMENT_AVAILABLE else 'Degraded: audio alignment unavailable',
            components=components,
            cache={
                'hit_rate': cache_stats_local.get('hit_rate'),
                'hits': cache_stats_local.get('hits'),
                'misses': cache_stats_local.get('misses'),
            },
            metrics=metrics_snapshot()
        )
        return jsonify(health)
    except Exception as e:  # noqa: BLE001
        return jsonify(error_response(str(e), error_type='unexpected_error', status=500)), 500

__all__ = ['system_bp']
