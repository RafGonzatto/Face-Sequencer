"""Application factory and base initialization split from monolithic app.py.

This module creates the Flask app, configures logging, error handling, SocketIO,
base config values and registers early utility blueprints. Heavy feature groups
(routes) are moved into dedicated blueprint modules under app_core.routes.*.
"""
from __future__ import annotations
import os
import logging
from flask import Flask
from exception_middleware import configure_app_error_handling
from config import config
from logger import app_logger

try:
    from flask_socketio import SocketIO  # type: ignore
    SOCKETIO_AVAILABLE = True
except Exception:  # pragma: no cover
    SocketIO = None  # type: ignore
    SOCKETIO_AVAILABLE = False


def create_app(test_mode: bool | None = None):
    if test_mode is None:
        test_mode = bool(os.environ.get('PYTEST_CURRENT_TEST') or os.environ.get('UNIT_TEST_MODE') == '1')
    app = Flask(
        __name__,
        static_url_path='/static',
        static_folder=str(config.paths.static_folder()),
        template_folder=str(config.paths.template_folder()),
    )

    # Base configuration
    app.config.update(
        UPLOAD_FOLDER=str(config.paths.upload_folder()),
        AUDIO_FOLDER=str(config.paths.audio_folder()),
        PROJECTS_FOLDER=str(config.paths.projects_folder()),
        ALLOWED_AUDIO_EXTENSIONS=config.limits.allowed_audio_extensions(),
        MAX_CONTENT_LENGTH=config.limits.max_upload_size(),
        TEST_MODE=test_mode,
    )

    # Error handling
    configure_app_error_handling(app)

    socketio = None
    if SOCKETIO_AVAILABLE and not test_mode:
        try:  # pragma: no cover - environment dependent
            socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
            app_logger.info("SocketIO initialized")
        except Exception as e:  # noqa: BLE001
            app_logger.warning(f"SocketIO init failed: {e}")

    # Attach simple state container
    app.config['app_state'] = {
        'current_project': None,  # Will be set later by project module
        'export_tasks': {},
    }

    # Late blueprint registration (lightweight imports) to avoid circular deps
    try:  # pragma: no cover - import side effects only
        from app_core.routes_alignment import alignment_bp  # type: ignore
        if 'alignment' not in [bp.name for bp in app.blueprints.values()]:
            app.register_blueprint(alignment_bp)
    except Exception as e:  # noqa: BLE001
        app_logger.debug(f"Alignment blueprint not registered in factory: {e}")
    try:  # pragma: no cover
        from app_core.routes_alignment_stream import stream_alignment_bp  # type: ignore
        if 'alignment_stream' not in [bp.name for bp in app.blueprints.values()]:
            app.register_blueprint(stream_alignment_bp)
    except Exception as e:  # noqa: BLE001
        app_logger.debug(f"Streaming alignment blueprint not registered: {e}")
    try:  # pragma: no cover
        from app_core.routes_sequence import sequence_bp  # type: ignore
        if 'sequence' not in [bp.name for bp in app.blueprints.values()]:
            app.register_blueprint(sequence_bp)
    except Exception as e:  # noqa: BLE001
        app_logger.debug(f"Sequence blueprint not registered: {e}")
    try:  # pragma: no cover
        from app_core.routes_export import export_legacy_bp  # type: ignore
        if 'export_legacy' not in [bp.name for bp in app.blueprints.values()]:
            app.register_blueprint(export_legacy_bp)
    except Exception as e:  # noqa: BLE001
        app_logger.debug(f"Export legacy blueprint not registered: {e}")
    try:  # pragma: no cover
        from app_core.routes_subtitles import subtitles_bp  # type: ignore
        if 'subtitles' not in [bp.name for bp in app.blueprints.values()]:
            app.register_blueprint(subtitles_bp)
    except Exception as e:  # noqa: BLE001
        app_logger.debug(f"Subtitles blueprint not registered: {e}")
    return app, socketio
