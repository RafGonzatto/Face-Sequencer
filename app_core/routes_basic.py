"""Basic UI and utility routes (index, folder scan, thumbnails, docs, status)"""
from __future__ import annotations
import os, string, base64, io
from flask import Blueprint, render_template, jsonify, request
from PIL import Image
from api_responses import success_response, error_response
from logger import app_logger
from lipanim_core_demo import load_letter_map_from_dir

basic_bp = Blueprint('basic', __name__)

@basic_bp.route('/', methods=['GET'])
def index():  # pragma: no cover - UI
    try:
        return render_template('index.html')
    except Exception as e:  # noqa: BLE001
        return f"<html><body><h1>UI Load Error</h1><pre>{e}</pre></body></html>", 500

@basic_bp.route('/api/folder/scan', methods=['POST'])
def folder_scan():
    try:
        data = request.get_json(silent=True) or {}
        folder_path = data.get('path') or ''
        if folder_path and not os.path.isabs(folder_path):
            folder_path = os.path.abspath(folder_path)
        if not folder_path or not os.path.isdir(folder_path):
            return jsonify(error_response('Invalid or missing folder path', error_type='invalid_input', status=400)), 400
        letter_map = load_letter_map_from_dir(folder_path)
        # Build mapping payload & store in app_state
        app_state = request.app.config['app_state'] if hasattr(request, 'app') else None  # fallback
        # Simplified: not persisting here in refactor stage
        mapping_payload = {}
        for letter in string.ascii_uppercase:
            if letter in letter_map:
                abs_path = letter_map[letter]
                mapping_payload[letter] = {'mapped': True, 'path': os.path.basename(abs_path), 'abs_path': abs_path}
            else:
                mapping_payload[letter] = {'mapped': False, 'path': None}
        return jsonify(success_response('Folder scanned', mapped_count=len(letter_map), total_letters=len(string.ascii_uppercase), mappings=mapping_payload))
    except Exception as e:  # noqa: BLE001
        app_logger.exception('Folder scan failed')
        return jsonify(error_response(str(e), error_type='unexpected_error', status=500)), 500

@basic_bp.route('/api/mapping/thumbnails', methods=['POST'])
def mapping_thumbnails():
    try:
        data = request.get_json(silent=True) or {}
        letters = data.get('letters') or []
        size = int(data.get('size') or 64)
        thumbnails = {}
        # This refactored thin version does not do full state-driven mapping; kept minimal.
        return jsonify(success_response('Thumbnails generated', thumbnails=thumbnails, requested=len(letters), generated=len(thumbnails), size=size))
    except Exception as e:  # noqa: BLE001
        return jsonify(error_response(str(e), error_type='unexpected_error', status=500)), 500
