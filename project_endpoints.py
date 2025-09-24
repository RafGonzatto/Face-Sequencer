"""Project management endpoints blueprint."""
from __future__ import annotations
from flask import Blueprint, request, jsonify, send_file
from werkzeug.utils import secure_filename
from datetime import datetime
import os, json
from api_responses import success_response, error_response
from project_templates import ProjectManager

project_bp = Blueprint('project', __name__)

def _get_state(app):
    return app.config['app_state']

@project_bp.record_once
def _on_load(state):  # attach existing project_manager if present, else create
    app = state.app
    if not hasattr(app, 'project_manager'):
        # Fallback creation (should already exist in app.py)
        try:
            app.project_manager = ProjectManager(projects_dir=str(app.config['PROJECTS_FOLDER']))  # type: ignore[attr-defined]
        except Exception:
            pass

@project_bp.route('/api/project/save', methods=['POST'])
def save_project():
    from flask import current_app
    try:
        data = request.get_json() or {}
        filename = data.get('filename', 'project.json')
        app_state = _get_state(current_app)
        project_data = {
            'name': app_state['current_project']['name'],
            'folder_path': app_state['current_project']['folder_path'],
            'fallback_image': app_state['current_project']['fallback_image'],
            'text': app_state['current_project']['text'],
            'settings': app_state['current_project']['settings'],
            'created_at': datetime.now().isoformat(),
            'version': '1.0'
        }
        project_path = os.path.join(current_app.config['UPLOAD_FOLDER'], secure_filename(filename))
        with open(project_path, 'w', encoding='utf-8') as f:
            json.dump(project_data, f, ensure_ascii=False, indent=2)
        return send_file(project_path, as_attachment=True, download_name=filename)
    except Exception as e:  # noqa: BLE001
        return jsonify(error_response(str(e), error_type='unexpected_error', status=400)), 400

@project_bp.route('/api/project/load', methods=['POST'])
def load_project():
    from flask import current_app
    try:
        if 'file' not in request.files:
            return jsonify(error_response('No file provided', error_type='upload_error', status=400)), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify(error_response('No file selected', error_type='upload_error', status=400)), 400
        project_data = json.load(file.stream)
        app_state = _get_state(current_app)
        app_state['current_project']['name'] = project_data.get('name', 'Loaded Project')
        app_state['current_project']['folder_path'] = project_data.get('folder_path', '')
        app_state['current_project']['fallback_image'] = project_data.get('fallback_image', '')
        app_state['current_project']['text'] = project_data.get('text', '')
        app_state['current_project']['settings'].update(project_data.get('settings', {}))
        app_state['current_project']['sequence'] = []
        app_state['current_project']['letter_map'] = {}
        return jsonify(success_response('Project loaded', project=app_state['current_project']))
    except Exception as e:  # noqa: BLE001
        return jsonify(error_response(str(e), error_type='unexpected_error', status=400)), 400

@project_bp.route('/api/project', methods=['GET'])
def get_current_project():
    """Return the current in-memory project state.

    Added to support front-end attempts to fetch existing project without uploading a file.
    """
    from flask import current_app
    try:
        app_state = _get_state(current_app)
        return jsonify(success_response('Current project', project=app_state['current_project']))
    except Exception as e:  # noqa: BLE001
        return jsonify(error_response(str(e), error_type='unexpected_error', status=400)), 400

@project_bp.route('/api/projects/recent', methods=['GET'])
def get_recent_projects():
    from flask import current_app
    try:
        pm = getattr(current_app, 'project_manager', None)
        recent_projects = pm.get_recent_projects() if pm else []
        return jsonify(success_response('Recent projects', projects=recent_projects))
    except Exception as e:  # noqa: BLE001
        return jsonify(error_response(str(e), error_type='unexpected_error', status=400)), 400

@project_bp.route('/api/projects/<path:project_path>/load', methods=['POST'])
def load_project_by_path(project_path):
    from flask import current_app
    try:
        pm = getattr(current_app, 'project_manager', None)
        if not pm:
            return jsonify(error_response('Project manager unavailable', error_type='unavailable', status=500)), 500
        project_data = pm.load_project(project_path)
        app_state = _get_state(current_app)
        app_state['current_project']['name'] = project_data.get('name', 'Loaded Project')
        app_state['current_project']['folder_path'] = project_data.get('folder_path', '')
        app_state['current_project']['fallback_image'] = project_data.get('fallback_image', '')
        app_state['current_project']['text'] = project_data.get('text', '')
        app_state['current_project']['settings'].update(project_data.get('settings', {}))
        app_state['current_project']['sequence'] = []
        app_state['current_project']['letter_map'] = {}
        return jsonify(success_response('Project loaded', project=app_state['current_project']))
    except Exception as e:  # noqa: BLE001
        return jsonify(error_response(str(e), error_type='unexpected_error', status=400)), 400

@project_bp.route('/api/projects/save-managed', methods=['POST'])
def save_managed_project():
    from flask import current_app
    try:
        data = request.get_json() or {}
        filename = data.get('filename')
        pm = getattr(current_app, 'project_manager', None)
        if not pm:
            return jsonify(error_response('Project manager unavailable', error_type='unavailable', status=500)), 500
        app_state = _get_state(current_app)
        project_data = {
            'name': app_state['current_project']['name'],
            'folder_path': app_state['current_project']['folder_path'],
            'fallback_image': app_state['current_project']['fallback_image'],
            'text': app_state['current_project']['text'],
            'settings': app_state['current_project']['settings'],
            'sequence': app_state['current_project']['sequence']
        }
        project_path = pm.save_project(project_data, filename)
        return jsonify(success_response('Project saved successfully', project_path=project_path))
    except Exception as e:  # noqa: BLE001
        return jsonify(error_response(str(e), error_type='unexpected_error', status=400)), 400

__all__ = ['project_bp']
