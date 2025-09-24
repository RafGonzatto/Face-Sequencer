"""Template endpoints blueprint."""
from __future__ import annotations
from flask import Blueprint, jsonify
from api_responses import success_response, error_response
from project_templates import ProjectTemplates

templates_bp = Blueprint('templates', __name__)

def _get_state(app):
    return app.config['app_state']

@templates_bp.route('/api/templates', methods=['GET'])
def get_templates():
    from flask import current_app
    try:
        templates = ProjectTemplates.list_templates()
        return jsonify(success_response('Templates list', templates=templates))
    except Exception as e:  # noqa: BLE001
        return jsonify(error_response(str(e), error_type='unexpected_error', status=400)), 400

@templates_bp.route('/api/templates/<template_name>/apply', methods=['POST'])
def apply_template(template_name):
    from flask import current_app
    try:
        state = _get_state(current_app)
        ProjectTemplates.apply_template(template_name, state['current_project'])
        return jsonify(success_response('Template applied', project=state['current_project']))
    except Exception as e:  # noqa: BLE001
        return jsonify(error_response(str(e), error_type='unexpected_error', status=400)), 400

__all__ = ['templates_bp']
