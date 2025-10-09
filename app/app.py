import os
from flask import Flask, render_template
try:
    from flask_cors import CORS  # type: ignore
except Exception:  # pragma: no cover
    CORS = None  # type: ignore

def create_app():
    app = Flask(__name__, template_folder='../templates', static_folder='../static')

    from app.core.utils.config import configure_app
    configure_app(app)

    from app.api.audio.routes import audio_bp
    from app.api.export.routes import export_bp
    from app.api.export.sse_routes import export_sse_bp
    from app.api.export.phase4_routes import phase4_export_bp
    from app.api.project.routes import project_bp
    from app.api.sequence.routes import phase3_api_bp
    from app.api.sequence.sequence_routes import sequence_bp
    from app.api.system.model_routes import model_bp
    from app.api.system.system_routes import system_bp
    from app.api.utils.routes import util_bp
    from app.api.utils.templates_routes import templates_bp
    from app.api.audio.routes_alignment import audio_align_bp
    from app.api.subtitles.routes import subtitles_bp

    app.register_blueprint(audio_bp)
    app.register_blueprint(export_bp)
    app.register_blueprint(export_sse_bp)
    app.register_blueprint(phase4_export_bp)
    app.register_blueprint(project_bp)
    app.register_blueprint(phase3_api_bp)
    app.register_blueprint(sequence_bp)
    app.register_blueprint(model_bp)
    app.register_blueprint(system_bp)
    app.register_blueprint(util_bp)
    app.register_blueprint(templates_bp)
    app.register_blueprint(audio_align_bp)
    app.register_blueprint(subtitles_bp)
    # Alignment endpoints (standard/enhanced) foram removidos do legado app_core.
    # TODO: Reintroduzir blueprint alignment em app/api/audio/alignment_routes.py futuramente.

    from app.core.utils.error_handlers import register_error_handlers
    register_error_handlers(app)
    from app.services.exception_middleware import register_exception_handlers
    register_exception_handlers(app)

    # CORS (dev) - permitir frontend local se extensão instalada
    if CORS:
        CORS(app, resources={r"/api/*": {"origins": "*"}})

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/face-animator')
    def face_animator():
        return render_template('index.html')

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))


