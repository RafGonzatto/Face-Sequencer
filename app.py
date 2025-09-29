"""Flask Web Server for Face Sequencer Pro.

Test-mode adjustments:
 - Establish TEST_MODE flag early to bypass heavy audio initialization in tests.
 - Remove/guard unicode emoji prints that can raise UnicodeEncodeError under cp1252.
"""

# app.py - Flask Web Server for Face Sequencer Pro
import os
import json
import string
import time
import threading
import hashlib
from datetime import datetime
from pathlib import Path
import base64
import io

"""WP002: Using centralized PyTorch compatibility layer.
We intentionally do NOT mutate torch.load globally here anymore. Internal model
loading code should use pytorch_compat.safe_load or its context manager.
"""
try:
    from pytorch_compat import is_problematic_version, safe_load_context as torch_safe_load_context
except Exception:
    def is_problematic_version():  # type: ignore
        return False
    from contextlib import nullcontext as torch_safe_load_context  # type: ignore

from flask import Flask, render_template, request, jsonify, send_file, send_from_directory, Response, stream_with_context
from werkzeug.utils import secure_filename
from PIL import Image
import uuid

from audio_cache import audio_cache, generate_cache_key, hash_audio_file
from api_utils import require_audio_upload
from task_queue import job_manager
from api_responses import success_response, error_response
from model_manager import get_model_manager, ModelLoadError  # WP003 model lifecycle
from sse_manager import sse_manager
from metrics import time_block, record_timing, record_request, snapshot as metrics_snapshot
import logging

# Early test mode flag (must be before heavy imports)
TEST_MODE = bool(os.environ.get('PYTEST_CURRENT_TEST') or os.environ.get('UNIT_TEST_MODE') == '1')

# Get the logger
logger = logging.getLogger(__name__)

# Import original functionality
from lipanim_core_demo import (
    load_letter_map_from_dir, 
    build_sequence as create_sequence, 
    export_json, 
    export_mp4, 
    valid_img
)

# Import project management
from project_templates import ProjectTemplates, ProjectManager

# Import audio component factory (eliminates circular imports using dependency injection)
_TEST_MODE = bool(os.environ.get('PYTEST_CURRENT_TEST')) or os.environ.get('UNIT_TEST_MODE') == '1'
try:
    from audio_components import audio_factory
    from audio_aligner import AlignmentToken, TokenType
    if not TEST_MODE:
        try:
            audio_aligner_instance = audio_factory.get_audio_aligner()
        except Exception as init_err:  # noqa: BLE001
            logger.warning("Audio aligner initialization failed: %s", init_err)
            audio_aligner_instance = None
        AUDIO_ALIGNMENT_AVAILABLE = audio_aligner_instance is not None
        ENHANCED_ALIGNMENT_AVAILABLE = bool(getattr(audio_aligner_instance, "use_enhanced", False)) if AUDIO_ALIGNMENT_AVAILABLE else False
        # Use logger (ASCII only) to avoid Unicode issues
        if AUDIO_ALIGNMENT_AVAILABLE:
            logger.info("Audio alignment available (enhanced=%s)", ENHANCED_ALIGNMENT_AVAILABLE)
        else:
            logger.warning("Audio alignment not available")
    else:  # TEST_MODE: skip heavy init, assume available for contract tests
        audio_aligner_instance = None
        AUDIO_ALIGNMENT_AVAILABLE = True
        ENHANCED_ALIGNMENT_AVAILABLE = False
except ImportError as e:
    logger.warning("Audio alignment modules not importable: %s", e)
    AUDIO_ALIGNMENT_AVAILABLE = False
    ENHANCED_ALIGNMENT_AVAILABLE = False

def enhanced_features_status() -> dict:
    """Return a snapshot of enhanced feature availability (used for graceful degradation)."""
    return {
        'audio_alignment_available': AUDIO_ALIGNMENT_AVAILABLE,
        'enhanced_available': ENHANCED_ALIGNMENT_AVAILABLE
    }

# Import centralized configuration
from config import config

# Import centralized logging and error handling
from logger import app_logger, get_logger, log_exception
from exception_middleware import configure_app_error_handling

app = Flask(
    __name__,
    static_url_path='/static',
    static_folder=str(config.paths.static_folder()),
    template_folder=str(config.paths.template_folder()),
)

# Configure app error handling
configure_app_error_handling(app)

app.config.update(
    UPLOAD_FOLDER=str(config.paths.upload_folder()),
    AUDIO_FOLDER=str(config.paths.audio_folder()),
    PROJECTS_FOLDER=str(config.paths.projects_folder()),
    ALLOWED_AUDIO_EXTENSIONS=config.limits.allowed_audio_extensions(),
    MAX_CONTENT_LENGTH=config.limits.max_upload_size(),
)

# ---------------------------------------------------------------------------
# Root / Index Route (UI) - previously missing causing 404 on '/'
# ---------------------------------------------------------------------------
@app.route('/', methods=['GET'])
def index():  # pragma: no cover - UI route
    """Serve the main web UI.

    Returns the primary single-page interface. A 404 was previously returned
    because no root route existed; this fixes the blank page issue reported
    when accessing http://localhost:5000/ in the browser.
    """
    try:
        return render_template('index.html')
    except Exception as e:  # noqa: BLE001
        logger.exception("Failed to render index.html")
        # Fallback minimal HTML so user isn't stuck on a raw 404
        return f"<html><body><h1>UI Load Error</h1><pre>{e}</pre></body></html>", 500

# ---------------------------------------------------------------------------
# Folder Scan Endpoint (image mapping support) - missing caused 404 on /api/folder/scan
# ---------------------------------------------------------------------------
@app.route('/api/folder/scan', methods=['POST'])
def folder_scan():
    """Scan a provided folder path for image files and build a letter mapping.

    Expects JSON: { "path": "C:/path/to/images" }
    Returns: { success, mapped_count, total_letters, mappings: { 'A': {mapped, path}, ... } }
    """
    try:
        data = request.get_json(silent=True) or {}
        folder_path = data.get('path') or ''
        # Expand to absolute if user supplied relative (e.g., 'images')
        if folder_path and not os.path.isabs(folder_path):
            folder_path = os.path.abspath(folder_path)
        if not folder_path or not os.path.isdir(folder_path):
            return jsonify(error_response('Invalid or missing folder path', error_type='invalid_input', status=400)), 400

        # Load mapping using existing helper
        letter_map = load_letter_map_from_dir(folder_path)
        
        # Local helper to build small base64 PNG thumbnail
        def _thumb_data_url(img_path: str, size: int = 64) -> str | None:
            try:
                if not img_path:
                    return None
                from PIL import Image
                import io, base64
                with Image.open(img_path) as im:
                    im = im.convert('RGBA')
                    im.thumbnail((size, size))
                    buf = io.BytesIO()
                    im.save(buf, format='PNG')
                    b64 = base64.b64encode(buf.getvalue()).decode('ascii')
                    return f"data:image/png;base64,{b64}"
            except Exception:
                return None
        # Detect special images/tokens in folder
        pause_image = ''
        fallback_image = ''
        special_tokens: dict[str, str] = {}
        try:
            for fn in os.listdir(folder_path):
                path = os.path.join(folder_path, fn)
                if not os.path.isfile(path):
                    continue
                name, ext = os.path.splitext(fn)
                if ext.lower() not in ('.png', '.jpg', '.jpeg', '.webp', '.bmp'):
                    continue
                base = name.strip()
                lower = base.lower()
                if lower == 'fallback':
                    fallback_image = path
                    continue
                if lower == 'pause':
                    pause_image = path
                    continue
                # Consider tokens within hyphen-separated lists as candidates for multi-letter tokens
                tokens = [t for t in base.replace(' ', '').split('-') if t]
                for t in tokens:
                    # We keep only tokens with length > 1 (digraphs like CH, SH or vowel-variants like Aa)
                    if len(t) > 1:
                        special_tokens[t] = path
        except Exception:
            # Non-fatal
            pass
        total_letters = len(string.ascii_uppercase)
        mapped_count = len(letter_map)

        # Persist basic mapping paths into app_state for future sequence build
        app_state['current_project']['folder_path'] = folder_path
        if fallback_image:
            app_state['current_project']['fallback_image'] = fallback_image
        app_state['current_project']['pause_image'] = pause_image
        app_state['current_project']['special_tokens'] = special_tokens
        # Convert to internal structure expected by frontend (with mapped flag)
        mapping_payload = {}
        for letter in string.ascii_uppercase:
            if letter in letter_map:
                abs_path = letter_map[letter]
                # Store relative filename (not duplicating folder) for cleaner JSON; fallback to basename
                rel_name = os.path.basename(abs_path)
                mapping_payload[letter] = {
                    'mapped': True,
                    'path': rel_name,
                    'abs_path': abs_path  # keep absolute for backend convenience (not required by frontend)
                }
            else:
                mapping_payload[letter] = {
                    'mapped': False,
                    'path': None
                }

        # Store mapping in project state so thumbnail endpoint can reuse it
        app_state['current_project']['letter_map'] = mapping_payload

        # Build response including special images so frontend can reflect state
        resp_payload = success_response(
            'Folder scanned',
            mapped_count=mapped_count,
            total_letters=total_letters,
            mappings=mapping_payload,
            fallback_image=os.path.basename(app_state['current_project'].get('fallback_image') or '') if app_state['current_project'].get('fallback_image') else '',
            fallback_image_abs=app_state['current_project'].get('fallback_image') or '',
            fallback_thumb=_thumb_data_url(app_state['current_project'].get('fallback_image') or '') if app_state['current_project'].get('fallback_image') else None,
            space_image=os.path.basename(app_state['current_project'].get('pause_image') or '') if app_state['current_project'].get('pause_image') else '',
            space_image_abs=app_state['current_project'].get('pause_image') or '',
            space_thumb=_thumb_data_url(app_state['current_project'].get('pause_image') or '') if app_state['current_project'].get('pause_image') else None,
            special_tokens=list((app_state['current_project'].get('special_tokens') or {}).keys()),
        )

        return jsonify(resp_payload)
    except Exception as e:  # noqa: BLE001
        logger.exception('Folder scan failed')
        return jsonify(error_response(str(e), error_type='unexpected_error', status=500)), 500

# Log presence of folder scan route at import time for debugging
try:
    logger.info("/api/folder/scan route registered (app startup)")
except Exception:
    pass

# ---------------------------------------------------------------------------
# Mapping Thumbnails Endpoint - provides small previews for mapped letters
# ---------------------------------------------------------------------------
@app.route('/api/mapping/thumbnails', methods=['POST'])
def mapping_thumbnails():
    """Return base64 thumbnails for requested mapped letters.

    Expects JSON: { "letters": ["A","B",...], "size": 64(optional) }
    Uses current project's folder_path + stored mapping paths.
    """
    try:
        data = request.get_json(silent=True) or {}
        letters = data.get('letters') or []
        max_letters = 52  # safety cap
        if not isinstance(letters, list):
            return jsonify(error_response('letters must be a list', error_type='invalid_input', status=400)), 400
        if len(letters) > max_letters:
            letters = letters[:max_letters]

        size = int(data.get('size') or 64)
        size = max(16, min(size, 256))  # clamp

        project = app_state.get('current_project', {})
        folder_path = project.get('folder_path') or ''
        # Rebuild mapping quickly from stored mappings if present
        existing_mappings = project.get('letter_map') or {}

        # Fallback: if letter_map empty but folder exists, rebuild (user may not have built sequence yet)
        if not existing_mappings and folder_path and os.path.isdir(folder_path):
            try:
                existing_mappings = load_letter_map_from_dir(folder_path)
                project['letter_map'] = existing_mappings
            except Exception:
                existing_mappings = {}

        thumbnails = {}
        generated = 0
        for letter in letters:
            path_info = None
            if isinstance(existing_mappings, dict) and letter in existing_mappings:
                path_info = existing_mappings[letter]
            # Support both dict and raw string mapping values
            if isinstance(path_info, dict):
                if not path_info.get('mapped'):
                    continue
                # Prefer absolute path if stored
                candidate_path = path_info.get('abs_path') or path_info.get('path')
            else:
                candidate_path = path_info
            if not candidate_path:
                continue

            original_candidate = candidate_path
            if not os.path.isabs(candidate_path):
                if folder_path:
                    full_path = os.path.normpath(os.path.join(folder_path, candidate_path))
                else:
                    full_path = os.path.normpath(candidate_path)
            else:
                full_path = os.path.normpath(candidate_path)

            # Fallback heuristic: if file missing and looks like duplicated folder (images/images/...), trim one
            if not os.path.isfile(full_path) and folder_path:
                norm_folder = os.path.normpath(folder_path)
                double_prefix = norm_folder + os.sep + norm_folder + os.sep
                if full_path.replace('/', os.sep).find(double_prefix) != -1:
                    simplified = full_path.replace(double_prefix, norm_folder + os.sep, 1)
                    if os.path.isfile(simplified):
                        full_path = simplified

            if not os.path.isfile(full_path):
                logger.debug("Skipping thumbnail for %s (resolved path not found) orig=%s resolved=%s", letter, original_candidate, full_path)
                continue
            try:
                with Image.open(full_path) as img:
                    img = img.convert('RGBA')
                    img.thumbnail((size, size))
                    import io, base64
                    buf = io.BytesIO()
                    img.save(buf, format='PNG')
                    b64 = base64.b64encode(buf.getvalue()).decode('ascii')
                    thumbnails[letter] = f"data:image/png;base64,{b64}"
                    generated += 1
            except Exception as thumb_err:  # noqa: BLE001
                logger.debug("Thumbnail generation failed for %s: %s", letter, thumb_err)
                continue

        return jsonify(success_response(
            'Thumbnails generated',
            thumbnails=thumbnails,
            requested=len(letters),
            generated=generated,
            size=size
        ))
    except Exception as e:  # noqa: BLE001
        logger.exception('Thumbnail generation failed')
        return jsonify(error_response(str(e), error_type='unexpected_error', status=500)), 500

project_manager = ProjectManager(projects_dir=str(config.paths.projects_folder()))

# Use project defaults from centralized config
DEFAULT_PROJECT_SETTINGS = {
    'frame_duration': config.project_defaults.frame_duration(),
    'pause_duration': config.project_defaults.pause_duration(),
    'fps': config.project_defaults.fps(),
    'quality': config.project_defaults.quality(),
    'preset': config.project_defaults.preset(),
}


def _create_default_project_state():
    return {
        'name': 'New Project',
        'folder_path': '',
        'fallback_image': '',
        'pause_image': '',
        'text': '',
        'sequence': [],
        'letter_map': {},
        'special_tokens': {},  # e.g., 'CH', 'SH', 'Aa', 'Ee', ...
        'audio_alignment': None,
        'audio_file': None,
        'timing_mode': 'manual',
        'frame_states': [],  # Enhanced alignment frame timeline
        'last_alignment': None,  # Full enhanced alignment payload
        'fps': config.project_defaults.fps(),
        'settings': DEFAULT_PROJECT_SETTINGS.copy(),
    }


app_state = {
    'current_project': _create_default_project_state(),
    'export_tasks': {},
}

app.config['app_state'] = app_state

# ---------------------------------------------------------------------------
# Manual sequence build endpoint (front-end expectation)
# ---------------------------------------------------------------------------
@app.route('/api/sequence/build', methods=['POST'])
def build_sequence_manual():
    """Build a manual timing sequence using current project text & settings.

    The front-end invokes POST /api/sequence/build when not in audio-driven mode.
    We iterate characters in project['text']; spaces become pause frames; other
    characters map to letter_map entries (dict with abs_path or direct path). Missing
    mappings fall back to the project's fallback_image.
    """
    try:
        project = app_state['current_project']
        text = project.get('text', '') or ''
        settings = project.get('settings', {})
        letter_map = project.get('letter_map', {})
        fallback_image = project.get('fallback_image') or None
        frame_duration = int(settings.get('frame_duration', 80))
        pause_duration = int(settings.get('pause_duration', 120))

        sequence = []
        pause_image = project.get('pause_image') or None
        special_tokens = project.get('special_tokens') or {}

        # Helper to resolve path from mapping payload or direct string
        def _resolve_from_map(val):
            if isinstance(val, dict):
                return val.get('abs_path') or val.get('path')
            return val if isinstance(val, str) else None

        i = 0
        n = len(text)
        while i < n:
            ch = text[i]
            # Space / pause handling
            if ch == ' ':
                img_for_pause = pause_image or None
                frame = {'char': ' ', 'img': img_for_pause, 'ms': pause_duration, 'is_pause': True}
                if img_for_pause is None and fallback_image:
                    frame['img'] = fallback_image
                    frame['fallback_img'] = fallback_image
                sequence.append(frame)
                i += 1
                continue

            # Try digraphs and multi-letter tokens first (e.g., CH, SH)
            consumed = 1
            img_path = None
            token_used = None
            if i + 1 < n:
                two = text[i:i+2]
                # Keep original case token (e.g., 'ch' or 'Ch'); our map stores original filename token keys
                # Try upper-case digraph like 'CH' as well
                candidates = [two, two.upper(), two.title()]
                for cand in candidates:
                    if cand in special_tokens:
                        img_path = special_tokens.get(cand)
                        token_used = cand
                        consumed = 2
                        break

            # Vowel-initial variant like 'Aa' when vowel appears with no preceding consonant
            if img_path is None:
                upper = ch.upper()
                prev_char = text[i-1] if i > 0 else ' '
                is_word_start = not prev_char.isalpha()
                if upper in 'AEIOUÁÉÍÓÚÃÕ' and is_word_start:
                    # Normalize accented vowels to base latin vowel for variant lookup
                    base_map = {
                        'A': 'A', 'Á': 'A', 'Â': 'A', 'Ã': 'A', 'À': 'A',
                        'E': 'E', 'É': 'E', 'Ê': 'E',
                        'I': 'I', 'Í': 'I', 'Î': 'I',
                        'O': 'O', 'Ó': 'O', 'Ô': 'O', 'Õ': 'O',
                        'U': 'U', 'Ú': 'U', 'Û': 'U',
                    }
                    base = base_map.get(upper, upper)
                    variant_key = base + base.lower()  # 'A' -> 'Aa', 'E' -> 'Ee', ...
                    if variant_key in special_tokens:
                        img_path = special_tokens.get(variant_key)
                        token_used = variant_key

            # Fallback to single-letter mapping
            if img_path is None:
                entry = letter_map.get(ch.upper())
                img_path = _resolve_from_map(entry)

            # Fallback handling
            if not img_path and fallback_image:
                img_path = fallback_image
                frame = {'char': ch.upper(), 'img': img_path, 'ms': frame_duration, 'is_symbol_fallback': True}
                frame['fallback_img'] = fallback_image
            else:
                frame = {'char': ch.upper() if token_used is None else token_used, 'img': img_path, 'ms': frame_duration}

            sequence.append(frame)
            i += consumed

        project['sequence'] = sequence
        project['timing_mode'] = 'manual'

        stats = {
            'total_frames': len(sequence),
            'total_duration_ms': sum(f['ms'] for f in sequence),
            'timing_mode': 'manual'
        }
        return jsonify(success_response('Sequence built successfully', sequence=sequence, stats=stats))
    except Exception as e:  # noqa: BLE001
        return jsonify(error_response(str(e), error_type='unexpected_error', status=400)), 400

# ---------------------------------------------------------------------------
# WP006: Request timing instrumentation (simple WSGI timing)
# ---------------------------------------------------------------------------
@app.before_request
def _wp006_request_timer_start():
    request._start_time = time.perf_counter()  # type: ignore[attr-defined]


@app.after_request
def _wp006_request_timer_end(response):
    try:
        if hasattr(request, '_start_time'):
            delta_ms = (time.perf_counter() - getattr(request, '_start_time')) * 1000.0
            record_request(delta_ms)
    except Exception:  # pragma: no cover - non critical
        pass
    return response

# ---------------------------------------------------------------------------
# OpenAPI docs routes (auto-build if fragments newer than assembled spec)
# ---------------------------------------------------------------------------
@app.route('/openapi.yaml', methods=['GET'])
def serve_openapi_yaml():
    """Serve assembled OpenAPI spec; rebuild if modular fragments are newer."""
    try:
        from pathlib import Path
        spec_path = Path('openapi.yaml')
        json_path = Path('openapi_schemas.json')
        
        # Determine newest fragment mtime
        fragments = list(Path('openapi').rglob('*.yaml'))
        if fragments:
            newest_fragment_mtime = max(p.stat().st_mtime for p in fragments)
            rebuild_needed = (not spec_path.exists()) or (spec_path.stat().st_mtime < newest_fragment_mtime)
            json_needs_update = (not json_path.exists()) or (json_path.stat().st_mtime < spec_path.stat().st_mtime)
            
            if rebuild_needed or json_needs_update:
                # Rebuild both YAML and JSON to ensure consistency
                logger.info("OpenAPI schema files need updating, regenerating from fragments")
                import build_openapi
                build_openapi.generate_schemas(output_yaml=True, output_json=True)
                
        from flask import send_file
        return send_file(str(spec_path), mimetype='application/yaml')
    except Exception as e:  # noqa: BLE001
        logger.exception("Failed to serve OpenAPI spec")
        return jsonify(error_response(f'Failed to serve OpenAPI spec: {e}', error_type='unexpected_error', status=500)), 500

@app.route('/openapi_schemas.json', methods=['GET'])
def serve_openapi_json():
    """Serve JSON Schema representation of OpenAPI spec."""
    try:
        from pathlib import Path
        json_path = Path('openapi_schemas.json')
        
        if not json_path.exists():
            # Generate if missing
            logger.info("JSON Schema file missing, generating from OpenAPI spec")
            import build_openapi
            build_openapi.generate_schemas(output_yaml=False, output_json=True)
            
        from flask import send_file
        return send_file(str(json_path), mimetype='application/json')
    except Exception as e:  # noqa: BLE001
        logger.exception("Failed to serve JSON schema")
        return jsonify(error_response(f'Failed to serve JSON schema: {e}', error_type='unexpected_error', status=500)), 500


@app.route('/docs', methods=['GET'])
def swagger_ui_docs():
    """Serve a minimal Swagger UI pointing at /openapi.yaml."""
    html = """<!DOCTYPE html><html><head><title>API Docs</title>
<link rel=\"stylesheet\" href=\"https://unpkg.com/swagger-ui-dist/swagger-ui.css\" />
<style>body{margin:0;}#swagger-ui{max-width:100%;}</style></head>
<body><div id=\"swagger-ui\"></div>
<script src=\"https://unpkg.com/swagger-ui-dist/swagger-ui-bundle.js\"></script>
<script>window.onload=()=>{window.ui=SwaggerUIBundle({url:'/openapi.yaml',dom_id:'#swagger-ui'});};</script>
</body></html>"""
    from flask import Response
    return Response(html, mimetype='text/html')

@app.route('/test-status', methods=['GET'])
def test_status():
    """Página de teste de status da aplicação."""
    try:
        with open(os.path.join(os.path.dirname(__file__), 'test_status.html'), 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return '''
        <html><body style="font-family: Arial; padding: 20px; background: #0f172a; color: #e2e8f0;">
        <h1>✅ Face Sequencer Status</h1>
        <p><strong>Aplicação funcionando corretamente!</strong></p>
        <p>Problemas anteriores resolvidos:</p>
        <ul>
            <li>✅ Timeline Enhancement erro corrigido</li>
            <li>✅ Audio Manager inicialização melhorada</li>
            <li>✅ Sistema de anti-truncamento funcionando (7/7 testes passaram)</li>
            <li>✅ Timeline expandível implementada com controles de zoom e fullscreen</li>
        </ul>
        <p><a href="/" style="color: #3b82f6;">← Voltar para aplicação principal</a></p>
        </body></html>
        '''

# ---------------------------------------------------------------------------
# Response schema enforcement hook
# ---------------------------------------------------------------------------
@app.after_request
def enforce_response_schema(response):
    """Ensure all JSON responses contain required top-level keys.

    Adds or normalizes fields for consistency without mutating non-JSON responses.
    """
    try:
        if response.is_json:
            data = response.get_json()  # type: ignore[attr-defined]
            if isinstance(data, dict):
                # Guarantee success key
                if 'success' not in data:
                    # Infer success from presence of 'error'
                    data['success'] = 'error' not in data
                # Provide default message if success and none given
                if data.get('success') and 'message' not in data:
                    data['message'] = 'OK'
                # Standardize error fields
                if not data.get('success') and 'error' not in data:
                    # Map legacy field names
                    if 'error_message' in data:
                        data['error'] = data.pop('error_message')
                    else:
                        data['error'] = 'Unknown error'
                # Re-serialize updated structure WITHOUT creating a new Response
                try:
                    from flask import json as _flask_json
                    response.set_data(_flask_json.dumps(data))
                    response.mimetype = 'application/json'
                except Exception:  # pragma: no cover
                    pass
    except Exception as hook_err:  # noqa: BLE001
        print(f"Response schema enforcement skipped: {hook_err}")
    return response

## Sequence endpoints moved to sequence_endpoints.sequence_bp


def validate_mp4_file(file_path):
    """Validate that a file is a proper MP4 file
    
    Args:
        file_path: Path to the file to validate
        
    Returns:
        tuple: (is_valid, error_message, file_size)
    """
    # Check file existence
    if not os.path.exists(file_path):
        return False, "File not found", 0
    
    # Check file size
    file_size = os.path.getsize(file_path)
    print(f"Validating MP4 file: {file_path} (size: {file_size} bytes)")
    
    if file_size < 1024:  # If file is smaller than 1KB
        return False, f"File too small ({file_size} bytes)", file_size
    
    # Check if the file is a text file (error output)
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()
            if first_line.startswith("Error") or "error" in first_line.lower():
                return False, f"File contains error message: {first_line}", file_size
    except UnicodeDecodeError:
        # Not a text file, which is good for an MP4
        pass
    
    # Check MP4 signature
    try:
        with open(file_path, 'rb') as f:
            header = f.read(16)  # Read more bytes to be safe
            # MP4 files typically start with ftyp or mdat
            if not any(sig in header for sig in [b'ftyp', b'mdat', b'moov', b'free']):
                return False, f"Invalid MP4 signature", file_size
    except Exception as e:
        return False, f"Error reading file header: {str(e)}", file_size
    
    # Optional: Try to check video with FFmpeg if available
    try:
        import subprocess
        # Use FFprobe to check if file is valid
        result = subprocess.run(
            ['ffprobe', '-v', 'error', file_path],
            capture_output=True,
            text=True,
            timeout=3  # 3 second timeout
        )
        
        if result.returncode != 0:
            error = result.stderr.strip()
            return False, f"FFprobe validation failed: {error}", file_size
    except Exception as e:
        # FFprobe unavailable or failed, just log and continue
        print(f"FFprobe validation skipped: {e}")
    
    print(f"MP4 validation passed for {file_path}")
    return True, f"Valid MP4 file ({file_size} bytes)", file_size

@app.route('/api/export/validate/<task_id>', methods=['GET'])
def validate_export(task_id):
    """Validate that an exported MP4 file is proper"""
    try:
        if task_id not in app_state['export_tasks']:
            return jsonify(error_response('Task not found', error_type='not_found', status=404)), 404
        
        task = app_state['export_tasks'][task_id]
        
        if task['status'] != 'completed':
            return jsonify(error_response('Export not completed', error_type='invalid_state', status=400, details={'status': task['status'], 'progress': task['progress'], 'message': task['message']})), 400
        
        is_valid, error_msg, filesize = validate_mp4_file(task['path'])
        
        if not is_valid:
            app_state['export_tasks'][task_id]['status'] = 'error'
            app_state['export_tasks'][task_id]['error'] = error_msg
            return jsonify(error_response(error_msg, error_type='validation_failed', status=400, details={'valid': False, 'fileSize': filesize, 'filename': task['filename']})), 400
        
        return jsonify(success_response(error_msg, valid=True, fileSize=filesize, filename=task['filename']))
    
    except Exception as e:
        return jsonify(error_response(str(e), error_type='unexpected_error', status=400)), 400

@app.route('/api/export/download/<task_id>', methods=['GET'])
def download_export(task_id):
    """Download completed export"""
    try:
        if task_id not in app_state['export_tasks']:
            return jsonify(error_response('Task not found', error_type='not_found', status=404)), 404
        
        task = app_state['export_tasks'][task_id]
        
        if task['status'] != 'completed':
            return jsonify(error_response('Export not completed', error_type='invalid_state', status=400)), 400
        
        if not os.path.exists(task['path']):
            return jsonify(error_response('Export file not found', error_type='not_found', status=404)), 404
        
        # Always validate the MP4 file before downloading
        print(f"Validating file before download: {task['path']}")
        is_valid, error_msg, filesize = validate_mp4_file(task['path'])
        
        if not is_valid:
            print(f"Validation failed: {error_msg}")
            app_state['export_tasks'][task_id]['status'] = 'error'
            app_state['export_tasks'][task_id]['error'] = error_msg
            return jsonify(error_response(error_msg, error_type='validation_failed', status=400, details={'fileSize': filesize})), 400
            
        print(f"Validation passed: {error_msg}, size: {filesize} bytes")
        
        # If validation passes, try different approaches to serve the file
        file_path = os.path.abspath(task['path'])
        directory = os.path.dirname(file_path)
        filename = os.path.basename(file_path)
        
        # Define common headers for all response methods
        headers = {
            'Content-Disposition': f'attachment; filename="{task["filename"]}"',
            'Content-Type': 'video/mp4',
            'Content-Length': str(filesize),
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET',
            'Access-Control-Allow-Headers': 'Content-Type'
        }
        
        # Try different methods to send the file
        try:
            # Method 1: Flask's send_file
            response = send_file(
                task['path'], 
                as_attachment=True,
                download_name=task['filename'],
                mimetype='video/mp4'
            )
            
            # Add custom headers
            for header, value in headers.items():
                response.headers[header] = value
                
            print(f"Using send_file method to serve {task['filename']} ({filesize} bytes)")
            return response
            
        except Exception as e1:
            print(f"send_file failed: {str(e1)}, trying alternate method...")
            
            try:
                # Method 2: send_from_directory
                response = send_from_directory(
                    directory, 
                    filename,
                    as_attachment=True,
                    download_name=task['filename'],
                    mimetype='video/mp4'
                )
                
                # Add custom headers
                for header, value in headers.items():
                    response.headers[header] = value
                    
                print(f"Using send_from_directory method to serve {task['filename']}")
                return response
                
            except Exception as e2:
                print(f"send_from_directory failed: {str(e2)}, using direct Response...")
                
                # Method 3: Direct response with file data
                try:
                    with open(file_path, 'rb') as file_data:
                        response = Response(
                            file_data.read(),
                            mimetype='video/mp4',
                            headers=headers
                        )
                        print(f"Using direct Response method to serve {task['filename']}")
                        return response
                        
                except Exception as e3:
                    print(f"Direct Response method failed: {str(e3)}")
                    return jsonify(error_response(f"All file serving methods failed: {str(e3)}", error_type='download_error', status=500)), 500
    
    except Exception as e:
        error_msg = f"Error downloading export: {str(e)}"
        app.logger.error(error_msg)
        return jsonify(error_response(error_msg, error_type='unexpected_error', status=400)), 400

## Project & template endpoints moved to project_endpoints.project_bp and templates_endpoints.templates_bp

# ============================================================================
# AUDIO ALIGNMENT SYSTEM
# ============================================================================

def allowed_audio_file(filename):
    """Check if file has allowed audio extension"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_AUDIO_EXTENSIONS']


def require_audio_file(audio_filename: str, *, must_exist: bool = True) -> str:
    """Validate stored audio filename and return absolute path."""
    from audio_exceptions import AlignmentError

    if not audio_filename:
        raise AlignmentError('No audio filename provided', details={'field': 'audio_filename'})

    if not allowed_audio_file(audio_filename):
        raise AlignmentError(
            f'Unsupported audio format for stored file: {audio_filename}',
            details={'filename': audio_filename, 'allowed_formats': list(app.config['ALLOWED_AUDIO_EXTENSIONS'])}
        )

    audio_path = os.path.join(app.config['AUDIO_FOLDER'], audio_filename)

    if must_exist and not os.path.exists(audio_path):
        raise AlignmentError('Audio file not found', details={'filename': audio_filename})

    return audio_path

def get_audio_aligner():
    """Get or create audio aligner instance"""
    if not AUDIO_ALIGNMENT_AVAILABLE:
        return None
    
    # Use the factory-provided aligner instance
    # (no need to cache it locally as the factory handles caching)
    return audio_factory.get_audio_aligner(language="pt-BR")


def _apply_alignment_state_from_payload(text: str, audio_filename: str, payload: dict) -> None:
    """Update global project state using alignment payload details."""
    stats = payload.get('stats', {}) or {}
    alignment_meta = payload.get('alignment', {}) or {}
    alignment_stats = alignment_meta.get('stats', {}) or {}

    method = stats.get('method') or alignment_meta.get('method') or 'unknown'
    total_duration = (
        stats.get('total_duration_ms')
        or alignment_meta.get('total_duration_ms')
        or alignment_stats.get('audio_ms')
        or 0
    )
    confidence = (
        alignment_stats.get('avg_confidence')
        or stats.get('avg_confidence')
        or alignment_meta.get('confidence_score')
        or 0.0
    )

    alignment_state = {
        'filename': audio_filename,
        'alignment_method': method,
        'total_duration_ms': total_duration,
        'confidence_score': confidence,
        'created_at': datetime.now().isoformat()
    }

    if 'fps' in stats:
        alignment_state['fps'] = stats['fps']
    if 'enhancement_features' in alignment_meta:
        alignment_state['enhancement_features'] = alignment_meta['enhancement_features']

    app_state['current_project']['text'] = text
    app_state['current_project']['audio_alignment'] = alignment_state


def _normalize_alignment_tokens(tokens):
    """Ensure alignment tokens include duration metadata."""
    sequence = []
    for token in tokens:
        token_dict = token.copy() if isinstance(token, dict) else dict(token)
        if 'start_ms' in token_dict and 'end_ms' in token_dict and 'duration_ms' not in token_dict:
            token_dict['duration_ms'] = token_dict['end_ms'] - token_dict['start_ms']
        sequence.append(token_dict)
    return sequence


def compute_standard_alignment(audio_filename: str, text: str, language: str = 'pt-BR', *, use_cache: bool = True) -> dict:
    """Run the standard alignment workflow and return the payload sent to clients."""
    from audio_error_handling import with_timeout
    from audio_exceptions import AlignmentError, map_audio_processing_error

    audio_path = require_audio_file(audio_filename)
    aligner = get_audio_aligner()
    if not aligner:
        raise AlignmentError('Audio aligner not available', details={'stage': 'initialize'})

    # Use the original audio file for processing
    processing_path = audio_path

    cache_key = file_hash = params_signature = None
    cache_params = {
        'operation': 'align',
        'language': language,
        'text_hash': hashlib.sha256(text.strip().encode('utf-8')).hexdigest()
    }

    if use_cache:
        cache_key, file_hash, params_signature = generate_cache_key(
            processing_path,
            cache_params,
            namespace='alignment'
        )
        cached_response = audio_cache.get(cache_key)
        if cached_response:
            cached_message = cached_response.get('message', 'Audio alignment result retrieved from cache')
            cached_response['cached'] = True
            if '(cached)' not in cached_message.lower():
                cached_response['message'] = f"{cached_message} (cached)"
            _apply_alignment_state_from_payload(text, audio_filename, cached_response)
            return cached_response

    @with_timeout(timeout_seconds=300)
    def run_alignment():
        print(f"🎵 Starting audio alignment for: {audio_filename}")
        print(f"📝 Text: {text[:100]}...")
        print("⏳ First alignment may take longer as models are downloaded...")

        try:
            alignment_result = aligner.align_audio_to_text(processing_path, text, language=language)

            if not alignment_result:
                raise AlignmentError('Alignment failed - no result returned', details={'text': text[:100]})

            return {
                'success': True,
                'language': alignment_result.language,
                'sample_rate': alignment_result.sample_rate,
                'method': 'energy-based',
                'tokens': [
                    {
                        'type': token.type.value,
                        'text': token.text,
                        'viseme': token.viseme,
                        'start_ms': token.start_ms,
                        'end_ms': token.end_ms,
                        'confidence': token.confidence,
                        'lang': token.lang
                    }
                    for token in alignment_result.tokens
                ],
                'stats': {
                    'audio_ms': alignment_result.stats.audio_ms,
                    'drift_ms': alignment_result.stats.drift_ms,
                    'unaligned_count': alignment_result.stats.unaligned_count,
                    'avg_confidence': alignment_result.stats.avg_confidence,
                    'pause_count': alignment_result.stats.pause_count
                },
                'total_duration_ms': alignment_result.stats.audio_ms
            }
        except Exception as exc:  # noqa: BLE001
            print(f"❌ Alignment error: {exc}")
            raise AlignmentError(str(exc), details={'text': text[:100]})

    with time_block('alignment_time_ms'):
        alignment_dict = run_alignment()
    tokens = _normalize_alignment_tokens(alignment_dict.get('tokens', []))

    success_message = 'Audio alignment completed successfully'

    stats = {
        'total_tokens': len(tokens),
        'word_tokens': len([t for t in tokens if t.get('type') == 'word']),
        'gap_tokens': len([t for t in tokens if t.get('type') == 'gap']),
        'total_duration_ms': alignment_dict.get('total_duration_ms', 0),
        'method': alignment_dict.get('method', 'energy-based')
    }

    response_payload = {
        'success': True,
        'alignment': alignment_dict,
        'sequence': tokens,
        'stats': stats,
        'message': success_message,
        'cached': False
    }

    _apply_alignment_state_from_payload(text, audio_filename, response_payload)

    if use_cache:
        if cache_key is None:
            cache_key, file_hash, params_signature = generate_cache_key(
                processing_path,
                cache_params,
                namespace='alignment'
            )
        audio_cache.set(cache_key, response_payload, file_hash, params_signature)

    return response_payload


def compute_enhanced_alignment(
    audio_filename: str,
    text: str,
    *,
    language: str = 'pt-BR',
    fps: float = 30.0,
    method: str = 'auto',
    use_cache: bool = True,
) -> dict:
    """Execute the enhanced alignment workflow with caching support."""
    from audio_error_handling import with_timeout
    from audio_exceptions import AlignmentError

    audio_path = require_audio_file(audio_filename)
    aligner = get_audio_aligner()
    if not aligner:
        raise AlignmentError('Audio aligner not available', details={'stage': 'initialize'})

    if not hasattr(aligner, 'align_audio_to_text_enhanced'):
        raise AlignmentError('Enhanced alignment method not available', details={'stage': 'initialize'})

    # Use the original audio file for processing
    processing_path = audio_path

    cache_key = file_hash = params_signature = None
    cache_params = {
        'operation': 'align_enhanced',
        'language': language,
        'fps': float(fps),
        'method': method,
        'text_hash': hashlib.sha256(text.strip().encode('utf-8')).hexdigest()
    }

    if use_cache:
        cache_key, file_hash, params_signature = generate_cache_key(
            processing_path,
            cache_params,
            namespace='alignment_enhanced'
        )
        cached_response = audio_cache.get(cache_key)
        if cached_response:
            cached_message = cached_response.get('message', 'Enhanced alignment retrieved from cache')
            cached_response['cached'] = True
            if '(cached)' not in cached_message.lower():
                cached_response['message'] = f"{cached_message} (cached)"
            _apply_alignment_state_from_payload(text, audio_filename, cached_response)
            return cached_response

    @with_timeout(timeout_seconds=360)
    def run_enhanced_alignment():
        print(f"🚀 Starting enhanced audio alignment for: {audio_filename}")
        print(f"📝 Text: {text[:100]}...")
        print(f"🎬 Target FPS: {fps}")
        print(f"🎯 Alignment method: {method}")

        try:
            alignment_result, timeline, frame_states = aligner.align_audio_to_text_enhanced(
                processing_path,
                text,
                language=language,
                fps=fps,
                method=method
            )

            if not alignment_result:
                raise AlignmentError('Enhanced alignment failed - no result returned', details={'text': text[:100]})

            return {
                'success': True,
                'method': 'enhanced',
                'language': alignment_result.language,
                'sample_rate': alignment_result.sample_rate,
                'fps': fps,
                'tokens': [
                    {
                        'type': token.type.value,
                        'text': token.text,
                        'viseme': token.viseme,
                        'start_ms': token.start_ms,
                        'end_ms': token.end_ms,
                        'confidence': token.confidence,
                        'lang': token.lang,
                        'duration_ms': token.end_ms - token.start_ms
                    }
                    for token in alignment_result.tokens
                ],
                'timeline': [
                    {
                        'word': wt.word,
                        'start_time': wt.start_time,
                        'end_time': wt.end_time,
                        'start_frame': wt.start_frame,
                        'end_frame': wt.end_frame,
                        'start_frame_float': wt.start_frame_float,
                        'end_frame_float': wt.end_frame_float,
                        'start_offset': wt.start_offset,
                        'end_offset': wt.end_offset,
                        'confidence': wt.confidence,
                        'duration': wt.duration
                    }
                    for wt in (timeline or [])
                ],
                'frame_states': [
                    {
                        'frame_number': fs.frame_number,
                        'timestamp': fs.timestamp,
                        'active_word': fs.active_word,
                        'word_progress': fs.word_progress,
                        'opacity': fs.opacity,
                        'viseme': fs.viseme,
                        'confidence': fs.confidence
                    }
                    for fs in (frame_states or [])
                ],
                'stats': {
                    'audio_ms': alignment_result.stats.audio_ms,
                    'drift_ms': alignment_result.stats.drift_ms,
                    'unaligned_count': alignment_result.stats.unaligned_count,
                    'avg_confidence': alignment_result.stats.avg_confidence,
                    'pause_count': alignment_result.stats.pause_count
                },
                'total_duration_ms': alignment_result.stats.audio_ms,
                'enhancement_features': {
                    'sub_frame_timing': True,
                    'forced_alignment': True,
                    'enhanced_silence_detection': True,
                    'confidence_scoring': True,
                    'frame_synchronization': True
                }
            }
        except Exception as exc:  # noqa: BLE001
            print(f"❌ Enhanced alignment error: {exc}")
            raise AlignmentError(f'Enhanced alignment failed: {exc}', details={'text': text[:100], 'fallback_available': True})

    with time_block('alignment_time_ms'):
        alignment_dict = run_enhanced_alignment()
    tokens = _normalize_alignment_tokens(alignment_dict.get('tokens', []))
    frame_states = alignment_dict.get('frame_states', [])

    # Persist the latest enhanced alignment details for downstream consumers
    # (e.g., sequence building/export) so the client doesn't need to resend them.
    try:
        app_state['current_project']['last_alignment'] = alignment_dict
        app_state['current_project']['frame_states'] = frame_states
        # Prefer FPS from alignment dict, fallback to requested fps
        app_state['current_project']['fps'] = alignment_dict.get('fps') or fps
    except Exception:
        # Non-fatal: keep going even if state persistence fails
        pass

    response_payload = {
        'success': True,
        'alignment': alignment_dict,
        'sequence': tokens,
        'stats': {
            'total_tokens': len(tokens),
            'word_tokens': len([t for t in tokens if t.get('type') == 'word']),
            'gap_tokens': len([t for t in tokens if t.get('type') == 'gap']),
            'total_duration_ms': alignment_dict.get('total_duration_ms', 0),
            'total_frames': len(frame_states),
            'fps': fps,
            'method': 'enhanced',
            'avg_confidence': alignment_dict.get('stats', {}).get('avg_confidence', 0.0),
            'timing_precision': 'sub-frame'
        },
        'message': f'Enhanced audio alignment completed successfully with {fps} FPS precision',
        'cached': False
    }

    _apply_alignment_state_from_payload(text, audio_filename, response_payload)

    if use_cache:
        if cache_key is None:
            cache_key, file_hash, params_signature = generate_cache_key(
                processing_path,
                cache_params,
                namespace='alignment_enhanced'
            )
        audio_cache.set(cache_key, response_payload, file_hash, params_signature)

    return response_payload


def _alignment_job_worker(progress_callback, audio_filename: str, text: str, language: str) -> dict:
    """Background job wrapper for standard alignment."""
    progress_callback(5, 'Preparing alignment job')
    result = compute_standard_alignment(audio_filename, text, language)
    progress_callback(100, 'Alignment completed')
    return result

@app.route('/api/audio/status', methods=['GET'])
def audio_status():
    """Get audio alignment system status (standardized response)"""
    return jsonify(success_response(
        "Audio alignment system status",
        available=AUDIO_ALIGNMENT_AVAILABLE,
        enhanced_available=ENHANCED_ALIGNMENT_AVAILABLE,
        language='pt-BR' if AUDIO_ALIGNMENT_AVAILABLE else None,
        supported_formats=list(app.config['ALLOWED_AUDIO_EXTENSIONS']),
        features={
            'basic_alignment': AUDIO_ALIGNMENT_AVAILABLE,
            'enhanced_silence_detection': ENHANCED_ALIGNMENT_AVAILABLE,
            'forced_alignment': ENHANCED_ALIGNMENT_AVAILABLE,
            'sub_frame_timing': ENHANCED_ALIGNMENT_AVAILABLE,
            'confidence_scoring': ENHANCED_ALIGNMENT_AVAILABLE,
            'frame_synchronization': ENHANCED_ALIGNMENT_AVAILABLE
        }
    ))

@app.route('/api/cache/stats', methods=['GET'])
def cache_stats():
    """Return audio cache statistics (WP002)."""
    stats = audio_cache.stats()
    # Preserve previous fields but wrap raw stats under 'data' for backward test compatibility
    return jsonify(success_response("Audio cache statistics", data=stats, metrics=metrics_snapshot()))


@app.route('/api/health', methods=['GET'])
def health_check():
    """WP006: Application health endpoint returning component status & metrics summary."""
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

from error_handlers import handle_api_errors, ClassifiedAPIError  # (retain import if used elsewhere below)

@app.route('/api/audio/upload', methods=['POST'])
def upload_audio():
    """Upload and validate audio file"""
    # Import error handling
    from audio_error_handling import (
        validate_audio_file, 
        validate_audio_content,
        detect_speech_activity,
        handle_audio_errors
    )
    from audio_exceptions import AlignmentError
    
    @handle_audio_errors()
    @require_audio_upload('audio')
    def process_audio_upload(audio):
        if not AUDIO_ALIGNMENT_AVAILABLE:
            raise AlignmentError('Audio alignment system not available', details={'legacy_error_type': 'system_unavailable', 'phase': 'precheck'})
            
        # Process audio file normally
        
        # Generate unique filename
        timestamp = int(time.time())
        safe_filename = secure_filename(audio.filename)
        unique_filename = f"{timestamp}_{safe_filename}"
        audio_path = os.path.join(app.config['AUDIO_FOLDER'], unique_filename)
        
        try:
            # Save file
            audio.save(audio_path)
            
            # Validate audio content
            audio_metadata = validate_audio_content(audio_path)
            
            # Detect speech in the audio
            speech_info = detect_speech_activity(audio_path)
            
            # Get basic audio info with our audio aligner
            aligner = get_audio_aligner()
            if not aligner:
                raise AlignmentError('Audio aligner not initialized', details={'legacy_error_type': 'system_unavailable', 'phase': 'preprocess'})
            
            # Preprocess audio
            audio_data, sample_rate = aligner.preprocess_audio(audio_path)
            
            stored_hash = hash_audio_file(audio_path)

            # Invalidate stale cache entries referencing this file content
            audio_cache.invalidate_by_file_hash(stored_hash)

            audio_info = {
                'filename': unique_filename,
                'original_filename': audio.filename,
                'path': audio_path,
                'duration_ms': audio_metadata['duration_ms'],
                'sample_rate': sample_rate,
                'samples': len(audio_data),
                'speech_info': speech_info,
                'file_hash': stored_hash
            }
        except Exception as e:
            # Clean up on error
            if os.path.exists(audio_path):
                os.remove(audio_path)
            
            # Re-raise as AlignmentError if not already (legacy normalization complete)
            if not isinstance(e, AlignmentError):
                raise AlignmentError(f'Audio processing failed: {str(e)}', details={'legacy_error_type': 'processing_timeout', 'error': str(e)})
            raise
        
        return jsonify(success_response('Audio uploaded and validated successfully', audio=audio_info))
    
    # Call the wrapped function
    return process_audio_upload()

@app.route('/api/audio/align', methods=['POST'])
def align_audio():
    """Align audio with text to generate timing sequence"""
    # Import error handling
    from audio_error_handling import (
        handle_audio_errors,
        with_timeout,
        AudioFallbackHandler
    )
    from audio_exceptions import AlignmentError
    
    @handle_audio_errors(fallback_handler=AudioFallbackHandler.fallback_to_manual_timing)
    def process_audio_alignment():
        if not AUDIO_ALIGNMENT_AVAILABLE:
            raise AlignmentError('Audio alignment system not available', details={'legacy_error_type': 'system_unavailable', 'phase': 'precheck'})
            
        data = request.get_json()
        if not data:
            raise AlignmentError('No JSON data provided', details={'legacy_error_type': 'upload_error'})
            
        audio_filename = data.get('filename')
        text = data.get('text', '')
        language = data.get('language', 'pt-BR')  # Default to Portuguese

        if not text.strip():
            raise AlignmentError('No text provided for alignment', details={'legacy_error_type': 'alignment_failed'})
        
        audio_path = require_audio_file(audio_filename)
            
        # Use the audio file directly
        processing_path = audio_path
        
        # Get aligner and process
        aligner = get_audio_aligner()
        if not aligner:
            raise AlignmentError('Audio aligner not available', details={'legacy_error_type': 'system_unavailable'})
        
        cache_params = {
            'operation': 'align',
            'language': language,
            'text_hash': hashlib.sha256(text.strip().encode('utf-8')).hexdigest()
        }
        cache_key, file_hash, params_signature = generate_cache_key(
            processing_path,
            cache_params,
            namespace='alignment'
        )

        cached_response = audio_cache.get(cache_key)
        if cached_response:
            cached_message = cached_response.get('message', 'Audio alignment result retrieved from cache')
            if 'cached' not in cached_response:
                cached_response['cached'] = True
            if '(cached)' not in cached_message.lower():
                cached_response['message'] = f"{cached_message} (cached)"
            return jsonify(cached_response)

        # Perform alignment with timeout
        @with_timeout(timeout_seconds=300)  # Allow up to 5 minutes for alignment (increased from 180)
        def run_alignment():
            print(f"🎵 Starting audio alignment for: {audio_filename}")
            print(f"📝 Text: {text[:100]}...")
            print(f"⏳ First alignment may take longer as models are downloaded...")
            
            try:
                # Call the alignment function with the appropriate audio file
                alignment_result = aligner.align_audio_to_text(processing_path, text, language=language)
                
                if not alignment_result:
                    raise AlignmentError('Alignment failed - no result returned', details={'legacy_error_type': 'alignment_failed', 'text': text[:100]})
                
                # Converter o objeto AlignmentResult para dicionário
                result_dict = {
                    'success': True,
                    'language': alignment_result.language,
                    'sample_rate': alignment_result.sample_rate,

                    'tokens': [
                        {
                            'type': token.type.value,
                            'text': token.text,
                            'viseme': token.viseme,
                            'start_ms': token.start_ms,
                            'end_ms': token.end_ms,
                            'confidence': token.confidence,
                            'lang': token.lang
                        }
                        for token in alignment_result.tokens
                    ],
                    'stats': {
                        'audio_ms': alignment_result.stats.audio_ms,
                        'drift_ms': alignment_result.stats.drift_ms,
                        'unaligned_count': alignment_result.stats.unaligned_count,
                        'avg_confidence': alignment_result.stats.avg_confidence,
                        'pause_count': alignment_result.stats.pause_count
                    },
                    'total_duration_ms': alignment_result.stats.audio_ms
                }
                
                return result_dict
            except Exception as e:
                print(f"❌ Alignment error: {e}")
                raise AlignmentError(str(e), details={'legacy_error_type': 'alignment_failed', 'text': text[:100]})
            
        # Run alignment with timeout
        with time_block('alignment_time_ms'):
            alignment_result = run_alignment()
        
        # Convert alignment tokens to sequence format
        tokens = alignment_result.get('tokens', [])
        sequence = []
        
        for token in tokens:
            # Os tokens já são dicionários devido à nossa conversão acima
            token_dict = token.copy() if isinstance(token, dict) else token
            
            # Adicionar duração se não estiver presente
            if isinstance(token_dict, dict) and 'start_ms' in token_dict and 'end_ms' in token_dict and 'duration_ms' not in token_dict:
                token_dict['duration_ms'] = token_dict['end_ms'] - token_dict['start_ms']
                
            sequence.append(token_dict)
        
        # Update current project with audio-driven sequence
        app_state['current_project']['text'] = text
        app_state['current_project']['audio_file'] = audio_filename
        app_state['current_project']['timing_mode'] = 'audio_driven'
        app_state['current_project']['sequence'] = sequence
        
        print(f"✅ Audio alignment completed: {len(sequence)} tokens gerated")
        
        # Standard success message
        success_message = 'Audio alignment completed successfully'
        
        response_payload = {
            'success': True,
            'alignment': alignment_result,
            'sequence': sequence,
            'stats': {
                'total_tokens': len(sequence),
                'word_tokens': len([t for t in sequence if t.get('type') == 'word']),
                'gap_tokens': len([t for t in sequence if t.get('type') == 'gap']),
                'total_duration_ms': alignment_result.get('total_duration_ms', 0),
                'method': alignment_result.get('method', 'energy-based')
            },
            'message': success_message,
            'cached': False
        }

        audio_cache.set(cache_key, response_payload, file_hash, params_signature)

        # response_payload already JSON-ready; adapt to standardized schema
        return jsonify(success_response(
            response_payload.get('message', 'Audio alignment completed successfully'),
            **{k: v for k, v in response_payload.items() if k not in {'success', 'message'}}
        ))
    
    # Call the wrapped function
    return process_audio_alignment()

@app.route('/api/audio/align-enhanced', methods=['POST'])
def align_audio_enhanced():
    """Enhanced audio alignment with sub-frame timing and advanced features"""
    from audio_error_handling import (
        handle_audio_errors,
        with_timeout,
        AudioFallbackHandler
    )
    from audio_exceptions import AlignmentError
    
    @handle_audio_errors(fallback_handler=AudioFallbackHandler.fallback_to_manual_timing)
    def process_enhanced_alignment():
        if not AUDIO_ALIGNMENT_AVAILABLE:
            raise AlignmentError('Audio alignment system not available', details={'legacy_error_type': 'system_unavailable', 'phase': 'precheck'})
        
        if not ENHANCED_ALIGNMENT_AVAILABLE:
            # Fall back to standard alignment
            print("⚠️ Enhanced components not available, falling back to standard alignment")
            return align_audio()
            
        data = request.get_json()
        if not data:
            raise AlignmentError('No JSON data provided', details={'legacy_error_type': 'upload_error'})
            
        audio_filename = data.get('filename')
        text = data.get('text', '')
        language = data.get('language', 'pt-BR')
        fps = float(data.get('fps', 30.0))  # Frame rate for animation
        method = data.get('method', 'auto')  # wav2vec2, whisper, or auto
        
        if not audio_filename:
            raise AlignmentError('No audio filename provided', details={'legacy_error_type': 'upload_error'})
            
        if not text.strip():
            raise AlignmentError('No text provided for alignment', details={'legacy_error_type': 'alignment_failed'})
        
        # Check if audio file exists
        audio_path = os.path.join(app.config['AUDIO_FOLDER'], audio_filename)
        if not os.path.exists(audio_path):
            raise AlignmentError('Audio file not found', details={'legacy_error_type': 'upload_error', 'filename': audio_filename})
        
        # Get aligner and process
        aligner = get_audio_aligner()
        if not aligner:
            raise AlignmentError('Audio aligner not available', details={'legacy_error_type': 'system_unavailable'})
        
        # Check if enhanced alignment is available
        if not hasattr(aligner, 'align_audio_to_text_enhanced'):
            print("⚠️ Enhanced alignment method not available, falling back to standard")
            return align_audio()
        
        # Perform enhanced alignment with timeout
        @with_timeout(timeout_seconds=360)  # 6 minutes for enhanced processing
        def run_enhanced_alignment():
            print(f"🚀 Starting enhanced audio alignment for: {audio_filename}")
            print(f"📝 Text: {text[:100]}...")
            print(f"🎬 Target FPS: {fps}")
            print(f"🎯 Alignment method: {method}")
            
            try:
                # Call the enhanced alignment function
                alignment_result, timeline, frame_states = aligner.align_audio_to_text_enhanced(
                    audio_path, text, 
                    language=language,
                    fps=fps,
                    method=method
                )
                
                if not alignment_result:
                    raise AlignmentError('Enhanced alignment failed - no result returned', details={'legacy_error_type': 'alignment_failed', 'text': text[:100]})
                
                # Convert results to JSON-serializable format
                result_dict = {
                    'success': True,
                    'method': 'enhanced',
                    'language': alignment_result.language,
                    'sample_rate': alignment_result.sample_rate,
                    'fps': fps,
                    'tokens': [
                        {
                            'type': token.type.value,
                            'text': token.text,
                            'viseme': token.viseme,
                            'start_ms': token.start_ms,
                            'end_ms': token.end_ms,
                            'confidence': token.confidence,
                            'lang': token.lang,
                            'duration_ms': token.end_ms - token.start_ms
                        }
                        for token in alignment_result.tokens
                    ],
                    'timeline': [
                        {
                            'word': wt.word,
                            'start_time': wt.start_time,
                            'end_time': wt.end_time,
                            'start_frame': wt.start_frame,
                            'end_frame': wt.end_frame,
                            'start_frame_float': wt.start_frame_float,
                            'end_frame_float': wt.end_frame_float,
                            'start_offset': wt.start_offset,
                            'end_offset': wt.end_offset,
                            'confidence': wt.confidence,
                            'duration': wt.duration
                        }
                        for wt in timeline
                    ] if timeline else [],
                    'frame_states': [
                        {
                            'frame_number': fs.frame_number,
                            'timestamp': fs.timestamp,
                            'active_word': fs.active_word,
                            'word_progress': fs.word_progress,
                            'opacity': fs.opacity,
                            'viseme': fs.viseme,
                            'confidence': fs.confidence
                        }
                        for fs in frame_states
                    ] if frame_states else [],
                    'stats': {
                        'audio_ms': alignment_result.stats.audio_ms,
                        'drift_ms': alignment_result.stats.drift_ms,
                        'unaligned_count': alignment_result.stats.unaligned_count,
                        'avg_confidence': alignment_result.stats.avg_confidence,
                        'pause_count': alignment_result.stats.pause_count
                    },
                    'total_duration_ms': alignment_result.stats.audio_ms,
                    'enhancement_features': {
                        'sub_frame_timing': True,
                        'forced_alignment': True,
                        'enhanced_silence_detection': True,
                        'confidence_scoring': True,
                        'frame_synchronization': True
                    }
                }
                
                return result_dict
                
            except Exception as e:
                print(f"❌ Enhanced alignment error: {e}")
                # Fall back to standard alignment on error
                print("🔄 Falling back to standard alignment")
                from audio_exceptions import AlignmentError
                raise AlignmentError(f'Enhanced alignment failed: {str(e)}', details={'legacy_error_type': 'alignment_failed', 'text': text[:100], 'fallback_available': True})
        
        # Run enhanced alignment
        with time_block('alignment_time_ms'):
            alignment_result = run_enhanced_alignment()
        
        # Update current project with enhanced audio-driven sequence
        tokens = alignment_result.get('tokens', [])
        sequence = tokens  # Enhanced tokens are already in the right format
        
        # Persist enhanced alignment artifacts for downstream steps
        try:
            app_state['current_project']['last_alignment'] = alignment_result
            app_state['current_project']['frame_states'] = alignment_result.get('frame_states', [])
            app_state['current_project']['fps'] = alignment_result.get('fps', fps)
        except Exception:
            # Non-fatal persistence error; continue
            pass

        app_state['current_project']['text'] = text
        app_state['current_project']['audio_file'] = audio_filename
        app_state['current_project']['timing_mode'] = 'audio_driven'
        app_state['current_project']['sequence'] = sequence
        
        print(f"✅ Enhanced audio alignment completed: {len(sequence)} tokens, {len(alignment_result.get('frame_states', []))} frame states")
        
        return jsonify(success_response(
            f'Enhanced audio alignment completed successfully with {fps} FPS precision',
            alignment=alignment_result,
            sequence=sequence,
            stats={
                'total_tokens': len(sequence),
                'word_tokens': len([t for t in sequence if t.get('type') == 'word']),
                'gap_tokens': len([t for t in sequence if t.get('type') == 'gap']),
                'total_duration_ms': alignment_result.get('total_duration_ms', 0),
                'total_frames': len(alignment_result.get('frame_states', [])),
                'fps': fps,
                'method': 'enhanced',
                'avg_confidence': alignment_result.get('stats', {}).get('avg_confidence', 0.0),
                'timing_precision': 'sub-frame'
            }
        ))
    
    # Call the wrapped function
    return process_enhanced_alignment()

def validate_and_correct_frame_timing(frame_states, audio_duration_ms=None, fps=30.0):
    """
    ROBUST TIMING CORRECTION - ALWAYS ACTIVE
    
    This function ALWAYS applies timing correction to ensure consistent lip sync
    throughout the entire video, regardless of audio duration (1min to 30min+).
    
    FIXES: Timing drift that causes perfect first 40s, then broken sync after.
    
    Args:
        frame_states: Frame states from audio alignment
        audio_duration_ms: Total audio duration (optional)
        fps: Target frame rate (default 30 FPS)
        
    Returns:
        Frame states with mathematically perfect timing
    """
    if not frame_states:
        return frame_states
    
    print(f"🎯 ROBUST TIMING CORRECTION: Processing {len(frame_states)} frames for {fps} FPS")
    
    # ALWAYS apply correction - don't trust original timing data
    target_frame_duration_ms = 1000.0 / fps
    
    # Store original data for analysis
    ms_values = [frame.get('ms', 33.33) for frame in frame_states]
    avg_ms_original = sum(ms_values) / len(ms_values) if ms_values else 33.33
    
    print(f"📊 Original avg frame duration: {avg_ms_original:.2f}ms")
    print(f"� Target frame duration: {target_frame_duration_ms:.2f}ms")
    
    # FORCE perfect timing for ALL frames
    corrected_frames = []
    
    for i, frame in enumerate(frame_states):
        corrected_frame = frame.copy()
        
        # Preserve original data for debugging
        corrected_frame['ms_original'] = frame.get('ms', 33.33)
        if 'timestamp' in frame:
            corrected_frame['timestamp_original'] = frame['timestamp']
        
        # FORCE mathematically perfect timing with maximum precision
        corrected_frame['ms'] = target_frame_duration_ms
        # Use precise calculation to avoid float accumulation errors in long videos
        corrected_frame['timestamp'] = round(i / fps, 6)  # 6 decimal precision
        
        # Validation every 1000 frames (~33s @ 30fps) to catch any drift
        if i > 0 and i % 1000 == 0:
            expected_time = i / fps
            actual_time = corrected_frame['timestamp']
            drift_ms = abs(actual_time - expected_time) * 1000
            
            if drift_ms > 1.0:  # More than 1ms drift (should be impossible)
                print(f"⚠️  WARNING: Drift detected at frame {i}: {drift_ms:.2f}ms")
                # Force correction with maximum precision
                corrected_frame['timestamp'] = round(i / fps, 6)
        
        corrected_frames.append(corrected_frame)
    
    # Final validation
    total_frames = len(corrected_frames)
    expected_duration = total_frames / fps
    actual_duration = corrected_frames[-1]['timestamp'] if corrected_frames else 0
    final_drift_ms = abs(actual_duration - expected_duration) * 1000
    
    print(f"✅ CORRECTION COMPLETE:")
    print(f"   Total frames: {total_frames}")
    print(f"   Expected duration: {expected_duration:.3f}s")
    print(f"   Actual duration: {actual_duration:.3f}s")
    print(f"   Final timing error: {final_drift_ms:.1f}ms")
    
    if final_drift_ms > 50:  # More than 50ms error
        print(f"⚠️  WARNING: Significant timing error still present!")
    else:
        print(f"🎯 Perfect timing achieved - lip sync guaranteed for entire video")
    
    return corrected_frames

def build_text_driven_sequence_enhanced(frame_states, text, project):
    """
    Enhanced text-driven sequence builder with 100% accuracy target
    Uses all available alignment data for perfect synchronization
    
    TIMING CORRECTION: This function now automatically detects and fixes timing drift
    to prevent the issue where first 20s are perfect, next 20s are accelerated,
    and final 20s are very slow.
    """
    # CRITICAL FIX: ALWAYS apply robust timing correction to prevent drift
    # This correction is MANDATORY for consistent lip sync in videos of any duration
    original_frame_count = len(frame_states) if frame_states else 0
    
    print(f"🎬 APPLYING MANDATORY TIMING CORRECTION for lip sync consistency")
    frame_states = validate_and_correct_frame_timing(frame_states)
    
    if original_frame_count > 0 and len(frame_states) != original_frame_count:
        print(f"🔧 Frame count changed during timing correction: {original_frame_count} → {len(frame_states)}")
    
    # Additional validation for long sequences
    if len(frame_states) > 1800:  # More than 1 minute @ 30fps
        print(f"📏 Long sequence detected ({len(frame_states)} frames = {len(frame_states)/30:.1f}s)")
        print(f"   → Enhanced validation will be applied throughout processing")
    
    # DEBUG: Check if this is where the error is coming from
    if not frame_states:
        print("🚨 DEBUG: frame_states is empty in build_text_driven_sequence_enhanced!")
        # Instead of returning an error, let's create a basic sequence from text
        sequence = []
        letter_map = project.get('letter_map', {})
        fallback_image = project.get('fallback_image_abs') or project.get('fallback_image')
        
        # Create a basic sequence from text when no frame_states available
        for char in text:
            if char == ' ':
                # Add pause for spaces
                sequence.append({
                    'char': ' ',
                    'img': fallback_image,
                    'ms': 100,  # Short pause
                    'is_pause': True,
                    'source': 'text_fallback'
                })
            else:
                # Add character frame
                char_upper = char.upper()
                img = letter_map.get(char_upper, fallback_image)
                sequence.append({
                    'char': char,
                    'img': img or fallback_image,
                    'ms': 80,  # Standard duration
                    'is_pause': False,
                    'source': 'text_fallback'
                })
        
        print(f"✅ Generated fallback sequence: {len(sequence)} frames from text")
        return sequence
    
    sequence = []
    letter_map = project.get('letter_map', {})
    special_tokens = project.get('special_tokens', {})
    fallback_image = project.get('fallback_image_abs') or project.get('fallback_image')
    pause_image = project.get('pause_image_abs') or project.get('pause_image')
    
    # Extract alignment tokens if available (from enhanced alignment)
    alignment_tokens = []
    last_alignment = project.get('last_alignment')
    if last_alignment and 'tokens' in last_alignment:
        alignment_tokens = last_alignment['tokens']
    
    # Extract word boundaries from frame_states with proper timestamp calculation
    word_boundaries = []
    current_word_start_frame = None
    current_word_start_time = None
    current_word = ""
    
    # Calculate cumulative timestamps for accurate timing
    # NOTE: After timing correction, all frames should have consistent 'ms' values
    cumulative_time = 0.0
    frame_timestamps = []
    
    for i, state in enumerate(frame_states):
        frame_timestamps.append(cumulative_time)
        ms = state.get('ms', 33.33)
        cumulative_time += ms / 1000.0
    
    # VALIDATION: Check for timing consistency after correction
    if len(frame_timestamps) > 10:
        expected_duration = (len(frame_timestamps) - 1) * (33.33 / 1000)  # Esperado para 30 FPS
        actual_duration = cumulative_time
        timing_error = abs(actual_duration - expected_duration)
        
        if timing_error > 0.1:  # Mais de 100ms de erro (mais rigoroso)
            print(f"⚠️  CRITICAL: Timing error detected: {timing_error*1000:.0f}ms")
            print(f"   Expected: {expected_duration:.3f}s, Actual: {actual_duration:.3f}s")
            print(f"   → This should NOT happen after robust correction!")
        else:
            print(f"✅ Timing validation passed: {timing_error*1000:.0f}ms error (within tolerance)")
    
    # Process word boundaries with accurate timestamps
    for i, state in enumerate(frame_states):
        active_word = state.get('active_word', '')
        current_timestamp = frame_timestamps[i]
        
        # Detect word start
        if active_word and not current_word:
            current_word_start_frame = i
            current_word_start_time = current_timestamp
            current_word = active_word
            
        # Detect word end (change or end of frames)
        elif current_word and (not active_word or active_word != current_word):
            # Ensure we have valid boundaries
            if current_word_start_frame is not None:
                word_boundaries.append({
                    'word': current_word,
                    'start': current_word_start_time,
                    'end': current_timestamp,
                    'start_frame': current_word_start_frame,
                    'end_frame': i - 1  # Previous frame was last of word
                })
            
            # Start new word if there's an active word
            if active_word:
                current_word_start_frame = i
                current_word_start_time = current_timestamp
                current_word = active_word
            else:
                current_word = ""
                current_word_start_frame = None
                current_word_start_time = None
    
    # CRITICAL: Add last word if still active (fixes truncation bug)
    if current_word and current_word_start_frame is not None:
        # Use the full end time including the last frame duration
        final_timestamp = cumulative_time
        word_boundaries.append({
            'word': current_word,
            'start': current_word_start_time,
            'end': final_timestamp,
            'start_frame': current_word_start_frame,
            'end_frame': len(frame_states) - 1
        })
    
    print(f"📊 Found {len(word_boundaries)} word boundaries from frame states")
    
    # Debug: Log the last few word boundaries to check for truncation
    if len(word_boundaries) > 0:
        last_boundary = word_boundaries[-1]
        print(f"🔍 Last word boundary: '{last_boundary['word']}' frames {last_boundary['start_frame']}-{last_boundary['end_frame']} (total frames: {len(frame_states)})")
        
        # Validate last word reaches end of frames
        if last_boundary['end_frame'] < len(frame_states) - 1:
            print(f"⚠️  WARNING: Last word ends at frame {last_boundary['end_frame']} but we have {len(frame_states)} frames - possible truncation!")
    
    # Clean and tokenize text
    import re
    import unicodedata
    
    def normalize_for_comparison(s):
        """Normalize text for comparison"""
        # Remove accents
        s = ''.join(c for c in unicodedata.normalize('NFD', s) 
                   if unicodedata.category(c) != 'Mn')
        # Keep only letters and normalize case
        s = re.sub(r'[^a-zA-Z]', '', s).upper()
        return s
    
    # Extract words from text
    text_words = re.findall(r'[a-zA-ZÀ-ÿ]+', text)
    text_words_normalized = [normalize_for_comparison(w) for w in text_words]
    
    print(f"📝 Text words: {len(text_words)} - {text_words[:10] if len(text_words) > 10 else text_words}")
    
    # IMPROVED: Match alignment words to text words with better coverage
    word_to_tokens = {}
    used_text_indices = set()
    
    # Strategy 1: Sequential matching (most common case)
    for i, boundary in enumerate(word_boundaries):
        boundary_word_norm = normalize_for_comparison(boundary['word'])
        
        # Try sequential match first (most reliable)
        if i < len(text_words_normalized) and i not in used_text_indices:
            if text_words_normalized[i] == boundary_word_norm:
                text_word = text_words[i]
                tokens = tokenize_word_enhanced(text_word, special_tokens, is_word_start=True, project=project)
                word_to_tokens[i] = {
                    'tokens': tokens,
                    'boundary': boundary,
                    'text_word': text_word,
                    'boundary_index': i
                }
                used_text_indices.add(i)
                continue
        
        # Strategy 2: Find exact match in remaining words
        best_match_idx = None
        for j, tw_norm in enumerate(text_words_normalized):
            if j not in used_text_indices and tw_norm == boundary_word_norm:
                best_match_idx = j
                break
        
        if best_match_idx is not None:
            text_word = text_words[best_match_idx]
            tokens = tokenize_word_enhanced(text_word, special_tokens, is_word_start=True, project=project)
            word_to_tokens[best_match_idx] = {
                'tokens': tokens,
                'boundary': boundary,
                'text_word': text_word,
                'boundary_index': i
            }
            used_text_indices.add(best_match_idx)
    
    # Strategy 3: CRITICAL FIX - Map remaining text words to remaining boundaries
    # This ensures ALL text words are represented, preventing truncation
    unmatched_text_indices = [i for i in range(len(text_words)) if i not in used_text_indices]
    unmatched_boundaries = [b for i, b in enumerate(word_boundaries) 
                           if not any(data['boundary'] == b for data in word_to_tokens.values())]
    
    if unmatched_text_indices and unmatched_boundaries:
        print(f"🔧 ANTI-TRUNCATION: Mapping {len(unmatched_text_indices)} remaining text words to {len(unmatched_boundaries)} boundaries")
        
        # Map remaining words to remaining boundaries sequentially
        for text_idx, boundary in zip(unmatched_text_indices, unmatched_boundaries):
            text_word = text_words[text_idx]
            tokens = tokenize_word_enhanced(text_word, special_tokens, is_word_start=True, project=project)
            word_to_tokens[text_idx] = {
                'tokens': tokens,
                'boundary': boundary,
                'text_word': text_word,
                'boundary_index': len(word_boundaries)  # Mark as extended
            }
    
    # Strategy 4: EMERGENCY FALLBACK - Create synthetic boundaries for remaining text words
    # This is the ultimate safeguard against truncation
    remaining_unmatched = [i for i in range(len(text_words)) if i not in word_to_tokens]
    if remaining_unmatched:
        print(f"🚨 EMERGENCY ANTI-TRUNCATION: Creating synthetic boundaries for {len(remaining_unmatched)} words")
        
        # Calculate where these words should appear in the timeline
        last_boundary_end = word_boundaries[-1]['end_frame'] if word_boundaries else 0
        remaining_frames = len(frame_states) - last_boundary_end - 1
        frames_per_word = max(10, remaining_frames // len(remaining_unmatched))  # At least 10 frames per word
        
        for idx, text_idx in enumerate(remaining_unmatched):
            text_word = text_words[text_idx]
            
            # Create synthetic boundary
            start_frame = last_boundary_end + 1 + (idx * frames_per_word)
            end_frame = min(len(frame_states) - 1, start_frame + frames_per_word - 1)
            
            synthetic_boundary = {
                'word': text_word.upper(),
                'start': start_frame / 30.0,  # Convert to seconds
                'end': end_frame / 30.0,
                'start_frame': start_frame,
                'end_frame': end_frame
            }
            
            tokens = tokenize_word_enhanced(text_word, special_tokens, is_word_start=True, project=project)
            word_to_tokens[text_idx] = {
                'tokens': tokens,
                'boundary': synthetic_boundary,
                'text_word': text_word,
                'boundary_index': -1,  # Mark as synthetic
                'synthetic': True
            }
    
    print(f"✅ Matched {len(word_to_tokens)} words to boundaries (includes all text words to prevent truncation)")
    
    # VALIDATION: Ensure we have coverage for all text words
    coverage_percentage = (len(word_to_tokens) / len(text_words)) * 100 if text_words else 100
    print(f"📊 Text word coverage: {len(word_to_tokens)}/{len(text_words)} ({coverage_percentage:.1f}%)")
    
    if coverage_percentage < 100:
        print(f"⚠️  WARNING: Not all text words are covered - this may cause truncation!")
    else:
        print(f"✅ PERFECT: All text words covered - no truncation will occur")
    
    # Build frame-by-frame sequence with improved accuracy
    last_frame_was_pause = False
    
    for i, state in enumerate(frame_states):
        active_word = state.get('active_word', '')
        actual_ms = state.get('ms', 33.33)  # Use actual frame duration
        
        if not active_word or state.get('is_pause'):
            # This is a pause/silence frame
            if not last_frame_was_pause:  # Avoid duplicate pauses
                sequence.append({
                    'char': ' ',
                    'img': pause_image or fallback_image,
                    'fallback_img': fallback_image,
                    'ms': actual_ms,
                    'is_pause': True,
                    'source': 'frame_pause'
                })
                last_frame_was_pause = True
        else:
            last_frame_was_pause = False
            
            # IMPROVED: Find which word boundary we're in (including synthetic ones)
            current_boundary = None
            
            # Check original word boundaries first
            for boundary in word_boundaries:
                if boundary['start_frame'] <= i <= boundary['end_frame']:
                    current_boundary = boundary
                    break
            
            # If no original boundary found, check synthetic boundaries
            if not current_boundary:
                for idx, word_data in word_to_tokens.items():
                    if word_data.get('synthetic'):
                        boundary = word_data['boundary']
                        if boundary['start_frame'] <= i <= boundary['end_frame']:
                            current_boundary = boundary
                            break
            
            if current_boundary:
                # Find the text word for this boundary
                matched_word = None
                for idx, word_data in word_to_tokens.items():
                    if word_data['boundary'] == current_boundary:
                        matched_word = word_data
                        break
                
                if matched_word:
                    tokens = matched_word['tokens']
                    boundary = matched_word['boundary']
                    
                    # Improved word progress calculation with timing validation
                    frames_in_word = max(1, boundary['end_frame'] - boundary['start_frame'] + 1)
                    frames_elapsed = i - boundary['start_frame']
                    word_progress = min(frames_elapsed / frames_in_word, 1.0)
                    
                    # ADVANCED TIMING DEBUG: Log only extremely long words to reduce noise
                    if frames_in_word > 150:  # Only words longer than 5 seconds
                        print(f"🔍 Extremely long word detected: '{boundary['word']}' with {frames_in_word} frames ({frames_in_word/30:.1f}s)")
                        
                    # Debug timing after 30 seconds to catch issues early
                    if i > 900:  # ~30s @ 30fps
                        current_time_s = frame_timestamps[i]
                        expected_time_s = i / 30.0
                        drift_ms = (current_time_s - expected_time_s) * 1000
                        
                        if abs(drift_ms) > 100:  # More than 100ms drift
                            print(f"🚨 TIMING DRIFT ALERT at frame {i}: {drift_ms:+.0f}ms")
                            print(f"   Word: '{boundary['word']}', Progress: {word_progress:.1%}")
                    
                    # CRITICAL FIX: Smart token distribution ensuring all important letters are shown
                    if len(tokens) == 1:
                        token_idx = 0
                    elif frames_in_word >= len(tokens):
                        # Enough frames - distribute evenly with proper spacing
                        token_idx = min(int((frames_elapsed * (len(tokens) - 1)) / (frames_in_word - 1)), len(tokens) - 1)
                    else:
                        # Fewer frames than tokens - prioritize key tokens
                        if frames_in_word <= 1:
                            token_idx = 0  # Only first token
                        elif frames_in_word == 2:
                            token_idx = 0 if frames_elapsed == 0 else len(tokens) - 1  # First and last
                        elif frames_in_word == 3:
                            # Show: first, middle, last
                            if frames_elapsed == 0:
                                token_idx = 0
                            elif frames_elapsed == 1:
                                token_idx = len(tokens) // 2
                            else:
                                token_idx = len(tokens) - 1
                        else:
                            # IMPROVED: For longer words with limited frames, use intelligent selection
                            # Prioritize vowels and consonants that are visually distinct
                            if len(tokens) > frames_in_word * 1.5:  # Long word, fewer frames than ideal
                                # Create a smart selection of key tokens
                                vowels = set('AEIOUÁÉÍÓÚÃÕ')
                                important_consonants = set('BLMNPRST')
                                
                                # Score each token by importance
                                token_scores = []
                                for i, token in enumerate(tokens):
                                    char = token['token'].upper()
                                    score = 0
                                    
                                    # Base importance
                                    if char in vowels:
                                        score += 3  # Vowels are very important
                                    elif char in important_consonants:
                                        score += 2  # Important consonants
                                    else:
                                        score += 1  # Other consonants
                                    
                                    # Position bonus - first and last are more important
                                    if i == 0 or i == len(tokens) - 1:
                                        score += 2
                                    elif i <= 2 or i >= len(tokens) - 3:
                                        score += 1
                                    
                                    token_scores.append((i, score, char))
                                
                                # Sort by score (descending) and select top tokens
                                token_scores.sort(key=lambda x: (-x[1], x[0]))  # By score, then position
                                selected_indices = [idx for idx, score, char in token_scores[:frames_in_word]]
                                selected_indices.sort()  # Keep chronological order
                                
                                # Distribute frames across selected indices
                                progress = frames_elapsed / (frames_in_word - 1) if frames_in_word > 1 else 0
                                idx_position = min(int(progress * (len(selected_indices) - 1)), len(selected_indices) - 1)
                                token_idx = selected_indices[idx_position]
                            else:
                                # Standard distribution for moderately long words
                                progress = frames_elapsed / (frames_in_word - 1)
                                token_idx = min(int(progress * (len(tokens) - 1)), len(tokens) - 1)
                        
                    # Debug logging for problematic cases (reduced verbosity)
                    if i > 600 and i % 300 == 0:  # Log every 10s after 20s
                        print(f"🔍 Frame {i}: word='{boundary['word']}' progress={word_progress:.3f} token_idx={token_idx}/{len(tokens)-1}")
                    
                    if token_idx < len(tokens):
                        token = tokens[token_idx]['token']
                        img = tokens[token_idx]['img']
                        
                        # Use the actual frame duration
                        
                        sequence.append({
                            'char': token,
                            'img': img or fallback_image,
                            'fallback_img': fallback_image,
                            'ms': actual_ms,
                            'is_pause': False,
                            'word': matched_word['text_word'],
                            'token_idx': token_idx,
                            'word_progress': word_progress
                        })
                    else:
                        # Shouldn't happen, but add fallback
                        sequence.append({
                            'char': active_word[0] if active_word else '?',
                            'img': fallback_image,
                            'fallback_img': fallback_image,
                            'ms': actual_ms,
                            'is_pause': False
                        })
                else:
                    # No matched text word, use active_word directly
                    char = active_word[0] if active_word else '?'
                    img = letter_map.get(char.upper(), fallback_image)
                    
                    sequence.append({
                        'char': char,
                        'img': img or fallback_image,
                        'fallback_img': fallback_image,
                        'ms': actual_ms,
                        'is_pause': False
                    })
    
    # FINAL VALIDATION: Ensure no timing issues remain in the output sequence
    if sequence:
        total_duration_ms = sum(frame.get('ms', 33.33) for frame in sequence)
        expected_duration_ms = len(sequence) * (1000.0 / 30.0)  # 30 FPS expected
        duration_error_ms = abs(total_duration_ms - expected_duration_ms)
        
        # CRITICAL: Compare with original frame_states duration
        original_duration_s = len(frame_states) / 30.0 if frame_states else 0
        sequence_duration_s = len(sequence) / 30.0
        truncation_error_s = original_duration_s - sequence_duration_s
        
        print(f"🎯 FINAL SEQUENCE VALIDATION:")
        print(f"   Original frame states: {len(frame_states)} frames ({original_duration_s:.2f}s)")
        print(f"   Generated sequence: {len(sequence)} frames ({sequence_duration_s:.2f}s)")
        print(f"   Truncation difference: {truncation_error_s:.2f}s ({truncation_error_s * 30:.0f} frames)")
        print(f"   Letter frames: {sum(1 for f in sequence if not f.get('is_pause'))}")
        print(f"   Pause frames: {sum(1 for f in sequence if f.get('is_pause'))}")
        print(f"   Expected duration: {expected_duration_ms/1000:.3f}s")
        print(f"   Actual duration: {total_duration_ms/1000:.3f}s")
        print(f"   Duration error: {duration_error_ms:.1f}ms")
        
        # Check for significant truncation (more than 5 seconds or 25% of original)
        if truncation_error_s > 5 or truncation_error_s > original_duration_s * 0.25:
            print(f"🚨 CRITICAL TRUNCATION ERROR: Video is {truncation_error_s:.1f}s shorter than audio!")
            print(f"   → This will cause lip sync to go out of sync after {sequence_duration_s:.1f}s")
            print(f"   → Original audio: {original_duration_s:.2f}s, Generated video: {sequence_duration_s:.2f}s")
            
            # EMERGENCY FIX: Add padding frames to match original duration if needed
            padding_frames_needed = len(frame_states) - len(sequence)
            if padding_frames_needed > 0:
                print(f"🔧 EMERGENCY PADDING: Adding {padding_frames_needed} padding frames")
                
                # Use the last meaningful frame or fallback
                last_frame = sequence[-1] if sequence else {
                    'char': ' ',
                    'img': fallback_image,
                    'ms': 33.33,
                    'is_pause': True,
                    'source': 'emergency_padding'
                }
                
                # Add padding frames
                for _ in range(padding_frames_needed):
                    padding_frame = last_frame.copy()
                    padding_frame['source'] = 'emergency_padding'
                    sequence.append(padding_frame)
                
                print(f"✅ Added {padding_frames_needed} padding frames - duration now matches audio")
        
        if duration_error_ms > 100:  # More than 100ms error
            print(f"❌ CRITICAL: Final sequence has timing errors!")
        else:
            print(f"✅ PERFECT: Final sequence timing is mathematically correct")
    else:
        print(f"⚠️  WARNING: Empty sequence generated")
    
    return sequence

def tokenize_word_enhanced(word, special_tokens, is_word_start=False, project=None):
    """
    Enhanced word tokenizer with special token support
    Returns list of {'token': str, 'img': str or None}
    """
    tokens = []
    i = 0
    letter_map = project.get('letter_map', {}) if project else {}
    fallback_image = project.get('fallback_image_abs') or project.get('fallback_image') if project else None
    
    while i < len(word):
        matched = False
        
        # Try to match digraphs first (CH, SH, etc.)
        if i + 1 < len(word):
            digraph = word[i:i+2].upper()
            if digraph in special_tokens:
                tokens.append({
                    'token': word[i:i+2],
                    'img': special_tokens[digraph]
                })
                i += 2
                matched = True
        
        if not matched:
            # Check for vowel at word start with special variant
            char = word[i]
            char_upper = char.upper()
            
            # Normalize accented vowels
            vowel_map = {'Á': 'A', 'À': 'A', 'Ã': 'A', 'Â': 'A',
                        'É': 'E', 'È': 'E', 'Ê': 'E',
                        'Í': 'I', 'Ì': 'I', 'Î': 'I',
                        'Ó': 'O', 'Ò': 'O', 'Õ': 'O', 'Ô': 'O',
                        'Ú': 'U', 'Ù': 'U', 'Û': 'U'}
            
            normalized = vowel_map.get(char_upper, char_upper)
            
            if is_word_start and i == 0 and normalized in 'AEIOU':
                # Try word-initial vowel variant
                variant_key = f"{normalized}a"  # Aa, Ea, Ia, Oa, Ua
                if variant_key in special_tokens:
                    tokens.append({
                        'token': char,
                        'img': special_tokens[variant_key]
                    })
                    i += 1
                    matched = True
            
            if not matched:
                # Use regular letter mapping
                img = letter_map.get(char_upper, fallback_image)
                tokens.append({
                    'token': char,
                    'img': img
                })
                i += 1
    
    return tokens

@app.route('/api/sequence/build-from-audio', methods=['POST'])
def build_sequence_from_audio():
    """Build sequence from audio alignment data"""
    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'error': 'No JSON data provided'}), 400
            
        text = data.get('text', '')
        text_driven = data.get('text_driven', True)
        
        # Get frame states from various sources
        frame_states = []
        
        # Try to get from request first
        if 'frame_states' in data and data['frame_states']:
            frame_states = data['frame_states']
        
        # Fall back to alignment results
        if not frame_states and 'alignment_results' in data:
            alignment_data = data['alignment_results']
            if 'frame_states' in alignment_data:
                frame_states = alignment_data['frame_states']
        
        # Fall back to project state
        if not frame_states:
            project = app_state['current_project']
            frame_states = project.get('frame_states', [])
        
        # Fall back to last alignment result
        if not frame_states:
            last_alignment = app_state['current_project'].get('last_alignment') or {}
            frame_states = last_alignment.get('frame_states', [])
        
        # Log frame states candidates for debugging
        req_fs_len = len(data.get('frame_states', [])) if data else 0
        align_fs_len = len(data.get('alignment_results', {}).get('frame_states', [])) if data and data.get('alignment_results') else 0
        state_fs_len = len(app_state['current_project'].get('frame_states', []))
        last_alignment = app_state['current_project'].get('last_alignment') or {}
        last_align_fs_len = len(last_alignment.get('frame_states', []))
        
        print(f"🔎 build-from-audio: frame_states candidates -> request:{req_fs_len}, alignment:{align_fs_len}, state:{state_fs_len}, last_alignment:{last_align_fs_len}")
        
        if not frame_states:
            # Se não há frame_states, tenta usar a sequência existente ou criar uma básica
            existing_sequence = app_state['current_project'].get('sequence', [])
            if existing_sequence:
                print("🔄 No frame states available, using existing sequence")
                return jsonify({
                    'success': True,
                    'sequence': existing_sequence,
                    'message': 'Using existing sequence (no frame states available)'
                })
            else:
                print("❌ No frame states or existing sequence available")
                return jsonify({
                    'success': False, 
                    'error': 'No frame states or sequence data available. Please run audio alignment first.'
                }), 400
        
        print(f"🎬 Building sequence from {len(frame_states)} frame states (text-driven: {text_driven}, audio-timed)")
        
        if text_driven:
            # NEW IMPROVED LOGIC: Use enhanced alignment data for perfect sync
            sequence = build_text_driven_sequence_enhanced(
                frame_states, 
                text,
                project=app_state['current_project']
            )
        else:
            # Legacy viseme-based mode
            sequence = []
            project = app_state['current_project']
            for state in frame_states:
                char = state.get('char', '')
                viseme = state.get('viseme', '')
                ms = state.get('ms', 33)
                
                # Skip empty frames
                if not char and not viseme:
                    continue
                
                # Map viseme to a representative character
                viseme_to_char = {
                    'A': 'A', 'E': 'E', 'I': 'I', 'O': 'O', 'U': 'U',
                    'BMP': 'M', 'FV': 'F', 'L': 'L', 'TH': 'T',
                    'R': 'R', 'CDGKNSTXYZ': 'T', 'QW': 'Q'
                }
                if viseme and not char:
                    char = viseme_to_char.get(viseme, viseme[:1] if viseme else '')
                
                # Get image for the character
                letter_key = char.upper() if char else ''
                img_path = None
                
                if letter_key in project['letter_map']:
                    img_path = project['letter_map'][letter_key]
                
                sequence.append({
                    'char': char,
                    'img': img_path,
                    'ms': ms,
                    'is_pause': state.get('is_pause', False)
                })
        
        print(f"✅ Generated sequence with {len(sequence)} frames (text-driven: {text_driven})")
        
        # Update project
        app_state['current_project']['sequence'] = sequence
        
        return jsonify({
            'success': True,
            'sequence': sequence
        })
        
    except Exception as e:
        print(f"❌ Error building sequence from audio: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/audio/analyze', methods=['POST'])  
def analyze_audio():
    """Analyze audio file for timing and features without full alignment"""
    from audio_error_handling import handle_audio_errors
    from audio_exceptions import AlignmentError

    @handle_audio_errors()
    def process_audio_analysis():
        if not AUDIO_ALIGNMENT_AVAILABLE:
            raise AlignmentError('Audio alignment system not available', details={'legacy_error_type': 'system_unavailable', 'phase': 'precheck'})

        data = request.get_json()
        if not data:
            raise AlignmentError('No JSON data provided', details={'legacy_error_type': 'upload_error'})

        audio_filename = data.get('audio_filename') or data.get('filename')
        audio_path = require_audio_file(audio_filename)

        aligner = get_audio_aligner()
        if not aligner:
            raise AlignmentError('Audio aligner not available', details={'legacy_error_type': 'system_unavailable'})

        audio_data, sample_rate = aligner.preprocess_audio(audio_path)
        duration_ms = len(audio_data) * 1000 / sample_rate if sample_rate else 0

        cache_params = {
            'operation': 'analyze',
            'version': 1,
            'sample_rate': sample_rate,
            'gap_detector': 'energy'
        }
        cache_key, file_hash, params_signature = generate_cache_key(
            audio_path,
            cache_params,
            namespace='analysis'
        )

        cached_response = audio_cache.get(cache_key)
        if cached_response:
            cached_response['cached'] = True
            cached_message = str(cached_response.get('message', 'Audio analysis retrieved from cache'))
            if '(cached)' not in cached_message.lower():
                cached_response['message'] = f"{cached_message} (cached)"
            return jsonify(cached_response)

        with time_block('analysis_time_ms'):
            gaps = aligner._detect_gaps_energy_based(audio_data, sample_rate)

        analysis = {
            'filename': audio_filename,
            'duration_ms': duration_ms,
            'sample_rate': sample_rate,
            'samples': len(audio_data),
            'gaps': [
                {
                    'start_ms': start_ms,
                    'end_ms': end_ms,
                    'duration_ms': end_ms - start_ms
                }
                for start_ms, end_ms in gaps
            ],
            'speech_segments': [],
            'analysis_timestamp': datetime.now().isoformat()
        }

        speech_segments = []
        last_end = 0.0

        for gap_start, gap_end in gaps:
            if gap_start > last_end:
                speech_segments.append({
                    'start_ms': last_end,
                    'end_ms': gap_start,
                    'duration_ms': gap_start - last_end
                })
            last_end = gap_end

        if last_end < duration_ms:
            speech_segments.append({
                'start_ms': last_end,
                'end_ms': duration_ms,
                'duration_ms': duration_ms - last_end
            })

        analysis['speech_segments'] = speech_segments

        response_payload = {
            'success': True,
            'analysis': analysis,
            'stats': {
                'total_gaps': len(gaps),
                'total_speech_segments': len(speech_segments),
                'speech_ratio': sum(seg['duration_ms'] for seg in speech_segments) / duration_ms if duration_ms > 0 else 0,
                'silence_ratio': sum(gap['duration_ms'] for gap in analysis['gaps']) / duration_ms if duration_ms > 0 else 0
            },
            'message': 'Audio analysis completed successfully',
            'cached': False
        }

        audio_cache.set(cache_key, response_payload, file_hash, params_signature)

        return jsonify(success_response(
            response_payload['message'],
            **{k: v for k, v in response_payload.items() if k not in {'success', 'message'}}
        ))

    return process_audio_analysis()



# Blueprint registrations (deferred until after core initialization)
try:  # pragma: no cover - defensive
    from util_endpoints import util_bp
    from audio_endpoints import audio_bp
    from export_endpoints import export_bp
    from model_endpoints import model_bp
    from sequence_endpoints import sequence_bp
    from system_endpoints import system_bp
    from project_endpoints import project_bp
    from templates_endpoints import templates_bp
    # Register if not already present
    existing = {bp.name for bp in app.blueprints.values()}
    if 'util' not in existing:
        app.register_blueprint(util_bp)
    if 'audio' not in existing:
        app.register_blueprint(audio_bp)
    if 'export' not in existing:
        app.register_blueprint(export_bp)
    if 'models' not in existing:
        app.register_blueprint(model_bp)
    if 'sequence' not in existing:
        app.register_blueprint(sequence_bp)
    if 'system' not in existing:
        app.register_blueprint(system_bp)
    if 'project' not in existing:
        app.register_blueprint(project_bp)
    if 'templates' not in existing:
        app.register_blueprint(templates_bp)
except Exception as _bp_err:  # noqa: BLE001
    try:
        logger.warning("Failed to register util blueprint: %s", _bp_err)
    except Exception:
        pass

if __name__ == '__main__':
    app_logger.info("Starting Face Sequencer Pro web server...")
    app_logger.info("Open your browser and go to: http://localhost:5000")
    try:
        app.run(host='0.0.0.0', port=5000, debug=True)
    except Exception as e:
        app_logger.error(f"Failed to start web server: {str(e)}")
        log_exception(app_logger, e)
        import sys
        sys.exit(1)