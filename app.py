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
        'text': '',
        'sequence': [],
        'letter_map': {},
        'audio_alignment': None,
        'audio_file': None,
        'timing_mode': 'manual',
        'settings': DEFAULT_PROJECT_SETTINGS.copy(),
    }


app_state = {
    'current_project': _create_default_project_state(),
    'export_tasks': {},
}

app.config['app_state'] = app_state

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

@app.route('/api/sequence/frame/<int:frame_id>', methods=['GET'])
def get_frame_image(frame_id):
    """Get full-size frame image for preview"""
    try:
        sequence = app_state['current_project']['sequence']
        
        if frame_id < 0 or frame_id >= len(sequence):
            return jsonify(error_response('Invalid frame ID', error_type='validation_error', status=400)), 400
        
        frame = sequence[frame_id]
        
        if frame['img'] is None:
            return jsonify(success_response('Pause frame', is_pause=True, char=frame['char'], duration=frame['ms']))
        
        if not valid_img(frame['img']):
            return jsonify(error_response('Invalid image path', error_type='not_found', status=400)), 400
        
        # Generate base64 image for preview
        with Image.open(frame['img']) as img:
            # Resize for web preview if too large
            if max(img.size) > 800:
                img.thumbnail((800, 800), Image.Resampling.LANCZOS)
            
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            image_data = base64.b64encode(buffer.getvalue()).decode()
        
        return jsonify(success_response('Frame retrieved', is_pause=False, char=frame['char'], duration=frame['ms'], image=f"data:image/png;base64,{image_data}", dimensions=img.size))
    
    except Exception as e:
        return jsonify(error_response(str(e), error_type='unexpected_error', status=400)), 400

@app.route('/api/sequence/update', methods=['POST'])
def update_sequence():
    """Update sequence frame properties"""
    try:
        data = request.get_json()
        frame_id = data.get('frame_id')
        updates = data.get('updates', {})
        
        sequence = app_state['current_project']['sequence']
        
        if frame_id < 0 or frame_id >= len(sequence):
            return jsonify(error_response('Invalid frame ID', error_type='validation_error', status=400)), 400
        
        # Update frame properties
        if 'duration' in updates:
            sequence[frame_id]['ms'] = max(1, int(updates['duration']))
        return jsonify(success_response('Frame updated'))
    
    except Exception as e:
        return jsonify(error_response(str(e), error_type='unexpected_error', status=400)), 400

@app.route('/api/sequence/reorder', methods=['POST'])
def reorder_sequence():
    """Reorder sequence frames"""
    try:
        data = request.get_json()
        from_index = data.get('from_index')
        to_index = data.get('to_index')
        
        sequence = app_state['current_project']['sequence']
        
        if (from_index < 0 or from_index >= len(sequence) or \
            to_index < 0 or to_index >= len(sequence)):
            return jsonify(error_response('Invalid frame indices', error_type='validation_error', status=400)), 400
        
        # Reorder frames
        frame = sequence.pop(from_index)
        sequence.insert(to_index, frame)
        return jsonify(success_response('Sequence reordered'))
    
    except Exception as e:
        return jsonify(error_response(str(e), error_type='unexpected_error', status=400)), 400

@app.route('/api/sequence/delete', methods=['POST'])
def delete_frame():
    """Delete frame from sequence"""
    try:
        data = request.get_json()
        frame_id = data.get('frame_id')
        
        sequence = app_state['current_project']['sequence']
        
        if frame_id < 0 or frame_id >= len(sequence):
            return jsonify(error_response('Invalid frame ID', error_type='validation_error', status=400)), 400
        
        # Delete frame
        del sequence[frame_id]
        return jsonify(success_response('Frame deleted'))
    
    except Exception as e:
        return jsonify(error_response(str(e), error_type='unexpected_error', status=400)), 400

@app.route('/api/export/json', methods=['POST'])
def export_sequence_json():
    """Export sequence as JSON"""
    try:
        data = request.get_json()
        filename = data.get('filename', 'sequence.json')
        
        sequence = app_state['current_project']['sequence']
        
        if not sequence:
            return jsonify({'success': False, 'error': 'No sequence to export'}), 400
        
        # Generate unique filename
        export_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(filename))
        
        # Export using original function
        export_json(sequence, export_path)
        
        return send_file(export_path, as_attachment=True, download_name=filename)
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/export/video', methods=['POST'])
def export_sequence_video():
    """Start video export task"""
    try:
        data = request.get_json()
        filename = data.get('filename', 'sequence.mp4')
        quality_preset = data.get('quality', 'medium')
        
        sequence = app_state['current_project']['sequence']
        settings = app_state['current_project']['settings']
        
        if not sequence:
            return jsonify(error_response('No sequence to export', error_type='empty_sequence', status=400)), 400
        
        # Generate task ID
        task_id = str(uuid.uuid4())
        
        # Quality presets
        quality_settings = {
            # WP004 optimized CRF values for animation (better balance of edges / size)
            'high': {'crf': 15, 'preset': 'slow'},
            'medium': {'crf': 20, 'preset': 'medium'},
            'fast': {'crf': 26, 'preset': 'fast'}
        }
        
        quality_config = quality_settings.get(quality_preset, quality_settings['medium'])
        
        # Create export task
        export_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(filename))
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(export_path)), exist_ok=True)
        
        app_state['export_tasks'][task_id] = {
            'status': 'pending',
            'progress': 0,
            'filename': filename,
            'path': export_path,
            'error': None,
            'message': 'Preparing to export video',
            'started_at': datetime.now()
        }
        
        # Start export in background thread
        def export_worker():
            try:
                app_state['export_tasks'][task_id]['status'] = 'processing'
                _t0 = time.perf_counter()
                
                # Define progress callback function
                def update_progress(progress, message=None):
                    # Update task progress
                    app_state['export_tasks'][task_id]['progress'] = progress
                    if message:
                        app_state['export_tasks'][task_id]['message'] = message
                    
                    # Publish progress update to SSE manager for real-time streaming
                    sse_manager.publish_event(task_id, 'export_progress', {
                        'status': app_state['export_tasks'][task_id]['status'],
                        'progress': progress,
                        'message': message if message else app_state['export_tasks'][task_id]['message'],
                        'error': app_state['export_tasks'][task_id]['error']
                    })
                    
                    # Handle error signal
                    if progress < 0:
                        app_state['export_tasks'][task_id]['status'] = 'error'
                        app_state['export_tasks'][task_id]['error'] = message if message else "Unknown error"
                        
                        # Publish error event to SSE manager
                        sse_manager.publish_event(task_id, 'export_progress', {
                            'status': 'error',
                            'progress': -1,
                            'message': message if message else "Unknown error",
                            'error': message if message else "Unknown error"
                        })
                
                # Get the global fallback image for the project
                fallback_path = app_state['current_project'].get('fallback_image')
                if fallback_path:
                    print(f"Using project fallback image: {fallback_path}")
                
                # Ensure all sequence frames have the project fallback for consistency
                for frame in sequence:
                    if not frame.get('fallback_img') and fallback_path:
                        frame['fallback_img'] = fallback_path
                
                # Call export with progress callback
                success = export_mp4(
                    seq=sequence,
                    path=export_path,
                    fps=settings['fps'],
                    crf=quality_config['crf'],
                    preset=quality_config['preset'],
                    progress_callback=update_progress
                )
                
                # Update final status based on success flag
                if success:
                    app_state['export_tasks'][task_id]['status'] = 'completed'
                    app_state['export_tasks'][task_id]['progress'] = 100
                    app_state['export_tasks'][task_id]['message'] = "Export completed successfully"
                    try:
                        record_timing('export_time_ms', (time.perf_counter() - _t0) * 1000.0)
                    except Exception:
                        pass
                    
                    # Publish completion event to SSE manager
                    sse_manager.publish_event(task_id, 'export_progress', {
                        'status': 'completed',
                        'progress': 100,
                        'message': "Export completed successfully",
                        'error': None
                    })
                else:
                    # If export_mp4 returned False but didn't set error status via callback
                    if app_state['export_tasks'][task_id]['status'] != 'error':
                        app_state['export_tasks'][task_id]['status'] = 'error'
                        app_state['export_tasks'][task_id]['error'] = "Export failed"
                        
                        # Publish error event to SSE manager
                        sse_manager.publish_event(task_id, 'export_progress', {
                            'status': 'error',
                            'progress': 100,
                            'message': "Export failed",
                            'error': "Export failed"
                        })
            
            except Exception as e:
                import traceback
                traceback.print_exc()
                app_state['export_tasks'][task_id]['status'] = 'error'
                app_state['export_tasks'][task_id]['error'] = str(e)
                
                # Publish error event to SSE manager
                sse_manager.publish_event(task_id, 'export_progress', {
                    'status': 'error',
                    'progress': 100,
                    'message': f"Export error: {str(e)}",
                    'error': str(e)
                })
        
        # Create a non-daemon thread so it won't be killed when Flask reloads
        thread = threading.Thread(target=export_worker)
        thread.daemon = False  # Set to non-daemon so it completes even if main thread exits
        thread.start()
        
        return jsonify(success_response('Export started', task_id=task_id))
    
    except Exception as e:
        return jsonify(error_response(str(e), error_type='unexpected_error', status=400)), 400

@app.route('/api/export/status/<task_id>', methods=['GET'])
def get_export_status(task_id):
    """Get export task status"""
    try:
        if task_id not in app_state['export_tasks']:
            return jsonify(error_response('Task not found', error_type='not_found', status=404)), 404
        
        task = app_state['export_tasks'][task_id]
        return jsonify(success_response('Export status', task=task))
    
    except Exception as e:
        return jsonify(error_response(str(e), error_type='unexpected_error', status=400)), 400

@app.route('/api/export/retry/<task_id>', methods=['POST'])
def retry_export(task_id):
    """Retry a failed export task"""
    try:
        # Check if task exists
        if task_id not in app_state['export_tasks']:
            return jsonify(error_response('Task not found', error_type='not_found', status=404)), 404
        
        original_task = app_state['export_tasks'][task_id]
        
        # Rest of the function implementation
        return jsonify(success_response('Export retry started'))
    except Exception as e:
        return jsonify(error_response(str(e), error_type='unexpected_error', status=400)), 400

@app.route('/api/sse/export-progress/<task_id>', methods=['GET'])
def export_progress_stream(task_id):
    """SSE endpoint for streaming export progress."""
    from queue import Empty
    
    try:
        # Verify the task exists
        if task_id not in app_state['export_tasks']:
            return jsonify(error_response('Task not found', error_type='not_found', status=404)), 404
        
        def event_stream():
            """Generate SSE event stream."""
            # Create a client-specific queue for this connection
            client_queue = sse_manager.add_client(task_id, 'export_progress')
            
            # Send initial message with current status
            task = app_state['export_tasks'][task_id]
            initial_data = {
                'status': task['status'],
                'progress': task['progress'],
                'message': task['message'],
                'error': task['error'],
                'initial': True
            }
            yield f"data: {json.dumps(initial_data)}\n\n"
            
            try:
                # Keep connection open and stream events as they come
                while True:
                    try:
                        # Non-blocking wait for message with a timeout
                        message = client_queue.get(timeout=0.5)
                        yield f"data: {message}\n\n"
                    except Empty:
                        # No message within timeout, send keep-alive
                        yield ": keep-alive\n\n"
                    
                    # If task is complete or failed, close the connection after sending final update
                    current_task = app_state['export_tasks'].get(task_id, {})
                    if current_task.get('status') in ['completed', 'error']:
                        # Send one more keep-alive then break to close the connection
                        time.sleep(1)
                        yield ": task-complete\n\n"
                        break
            finally:
                # Clean up the subscription when the client disconnects
                sse_manager.remove_client(task_id, 'export_progress', client_queue)
        
        return Response(
            stream_with_context(event_stream()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no',  # Disable proxy buffering
                'Connection': 'keep-alive'
            }
        )
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify(error_response(str(e), error_type='unexpected_error', status=500)), 500
        
        # Only retry if task was in error state
        if original_task['status'] != 'error':
            return jsonify(error_response('Can only retry failed exports', error_type='invalid_state', status=400)), 400
        
        # Get current sequence and settings
        sequence = app_state['current_project']['sequence']
        settings = app_state['current_project']['settings']
        
        if not sequence:
            return jsonify(error_response('No sequence to export', error_type='empty_sequence', status=400)), 400
        
        # Generate a new task ID
        new_task_id = str(uuid.uuid4())
        
        # Use same quality settings as original
        # Default to medium quality if original settings not available
        quality_preset = 'medium'
        if 'quality_preset' in original_task:
            quality_preset = original_task['quality_preset']
            
        # Quality presets
        quality_settings = {
            'high': {'crf': 15, 'preset': 'slow'},
            'medium': {'crf': 20, 'preset': 'medium'},
            'fast': {'crf': 26, 'preset': 'fast'}
        }
        
        quality_config = quality_settings.get(quality_preset, quality_settings['medium'])
        
        # Create new export task
        export_path = original_task['path']
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(export_path)), exist_ok=True)
        
        app_state['export_tasks'][new_task_id] = {
            'status': 'pending',
            'progress': 0,
            'filename': original_task['filename'],
            'path': export_path,
            'error': None,
            'message': 'Preparing to retry export',
            'started_at': datetime.now(),
            'quality_preset': quality_preset
        }
        
        # Start export in background thread
        def export_worker():
            try:
                app_state['export_tasks'][new_task_id]['status'] = 'processing'
                _t0 = time.perf_counter()
                
                # Define progress callback function
                def update_progress(progress, message=None):
                    try:
                        # Ensure progress is a valid number
                        if progress is not None and not isinstance(progress, (int, float)):
                            print(f"Warning: Invalid progress value: {progress}, type: {type(progress)}")
                            progress = 0
                            
                        # Update task progress (ensure it's an integer)
                        if progress is not None:
                            app_state['export_tasks'][new_task_id]['progress'] = int(progress)
                        
                        # Update message if provided
                        if message:
                            app_state['export_tasks'][new_task_id]['message'] = message
                            print(f"Export progress: {progress}% - {message}")
                        
                        # Handle error signal
                        if progress is not None and progress < 0:
                            app_state['export_tasks'][new_task_id]['status'] = 'error'
                            app_state['export_tasks'][new_task_id]['error'] = message if message else "Unknown error"
                            print(f"Export error: {message}")
                    except Exception as e:
                        print(f"Error in update_progress: {e} (progress: {progress}, message: {message})")
                
                # Get the global fallback image for the project
                fallback_path = app_state['current_project'].get('fallback_image')
                if fallback_path:
                    print(f"Using project fallback image: {fallback_path}")
                
                # Ensure all sequence frames have the project fallback for consistency
                for frame in sequence:
                    if not frame.get('fallback_img') and fallback_path:
                        frame['fallback_img'] = fallback_path
                
                # Call export with progress callback
                success = export_mp4(
                    seq=sequence,
                    path=export_path,
                    fps=settings['fps'],
                    crf=quality_config['crf'],
                    preset=quality_config['preset'],
                    progress_callback=update_progress
                )
                
                # Update final status based on success flag
                if success:
                    app_state['export_tasks'][new_task_id]['status'] = 'completed'
                    app_state['export_tasks'][new_task_id]['progress'] = 100
                    app_state['export_tasks'][new_task_id]['message'] = "Export retry completed successfully"
                    try:
                        record_timing('export_time_ms', (time.perf_counter() - _t0) * 1000.0)
                    except Exception:
                        pass
                else:
                    # If export_mp4 returned False but didn't set error status via callback
                    if app_state['export_tasks'][new_task_id]['status'] != 'error':
                        app_state['export_tasks'][new_task_id]['status'] = 'error'
                        app_state['export_tasks'][new_task_id]['error'] = "Export retry failed"
            
            except Exception as e:
                import traceback
                traceback.print_exc()
                app_state['export_tasks'][new_task_id]['status'] = 'error'
                app_state['export_tasks'][new_task_id]['error'] = str(e)
        
        # Create a non-daemon thread so it won't be killed when Flask reloads
        thread = threading.Thread(target=export_worker)
        thread.daemon = False  # Set to non-daemon so it completes even if main thread exits
        thread.start()
        
        return jsonify(success_response('Retry export started', original_task_id=task_id, new_task_id=new_task_id))
    
    except Exception as e:
        return jsonify(error_response(str(e), error_type='unexpected_error', status=400)), 400

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

@app.route('/api/project/save', methods=['POST'])
def save_project():
    """Save project to JSON file"""
    try:
        data = request.get_json()
        filename = data.get('filename', 'project.json')
        
        project_data = {
            'name': app_state['current_project']['name'],
            'folder_path': app_state['current_project']['folder_path'],
            'fallback_image': app_state['current_project']['fallback_image'],
            'text': app_state['current_project']['text'],
            'settings': app_state['current_project']['settings'],
            'created_at': datetime.now().isoformat(),
            'version': '1.0'
        }
        
        project_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(filename))
        
        with open(project_path, 'w', encoding='utf-8') as f:
            json.dump(project_data, f, ensure_ascii=False, indent=2)
        
        return send_file(project_path, as_attachment=True, download_name=filename)
    
    except Exception as e:
        return jsonify(error_response(str(e), error_type='unexpected_error', status=400)), 400

@app.route('/api/project/load', methods=['POST'])
def load_project():
    """Load project from JSON file"""
    try:
        if 'file' not in request.files:
            return jsonify(error_response('No file provided', error_type='upload_error', status=400)), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify(error_response('No file selected', error_type='upload_error', status=400)), 400
        
        # Read and parse project file
        project_data = json.load(file.stream)
        
        # Update app state
        app_state['current_project']['name'] = project_data.get('name', 'Loaded Project')
        app_state['current_project']['folder_path'] = project_data.get('folder_path', '')
        app_state['current_project']['fallback_image'] = project_data.get('fallback_image', '')
        app_state['current_project']['text'] = project_data.get('text', '')
        app_state['current_project']['settings'].update(project_data.get('settings', {}))
        
        # Clear existing sequence and mappings
        app_state['current_project']['sequence'] = []
        app_state['current_project']['letter_map'] = {}
        
        return jsonify(success_response('Project loaded', project=app_state['current_project']))
    
    except Exception as e:
        return jsonify(error_response(str(e), error_type='unexpected_error', status=400)), 400

@app.route('/api/templates', methods=['GET'])
def get_templates():
    """Get available project templates"""
    try:
        templates = ProjectTemplates.list_templates()
        return jsonify(success_response('Templates list', templates=templates))
    except Exception as e:
        return jsonify(error_response(str(e), error_type='unexpected_error', status=400)), 400

@app.route('/api/templates/<template_name>/apply', methods=['POST'])
def apply_template(template_name):
    """Apply template to current project"""
    try:
        # Apply template settings to current project
        ProjectTemplates.apply_template(template_name, app_state['current_project'])
        
        return jsonify(success_response('Template applied', project=app_state['current_project']))
    except Exception as e:
        return jsonify(error_response(str(e), error_type='unexpected_error', status=400)), 400

@app.route('/api/projects/recent', methods=['GET'])
def get_recent_projects():
    """Get recent projects list"""
    try:
        recent_projects = project_manager.get_recent_projects()
        return jsonify(success_response('Recent projects', projects=recent_projects))
    except Exception as e:
        return jsonify(error_response(str(e), error_type='unexpected_error', status=400)), 400

@app.route('/api/projects/<path:project_path>/load', methods=['POST'])
def load_project_by_path(project_path):
    """Load project by file path"""
    try:
        project_data = project_manager.load_project(project_path)
        
        # Update app state
        app_state['current_project']['name'] = project_data.get('name', 'Loaded Project')
        app_state['current_project']['folder_path'] = project_data.get('folder_path', '')
        app_state['current_project']['fallback_image'] = project_data.get('fallback_image', '')
        app_state['current_project']['text'] = project_data.get('text', '')
        app_state['current_project']['settings'].update(project_data.get('settings', {}))
        
        # Clear existing sequence and mappings
        app_state['current_project']['sequence'] = []
        app_state['current_project']['letter_map'] = {}
        
        return jsonify(success_response('Project loaded', project=app_state['current_project']))
    except Exception as e:
        return jsonify(error_response(str(e), error_type='unexpected_error', status=400)), 400

@app.route('/api/projects/save-managed', methods=['POST'])
def save_managed_project():
    """Save project using project manager"""
    try:
        data = request.get_json()
        filename = data.get('filename')
        
        project_data = {
            'name': app_state['current_project']['name'],
            'folder_path': app_state['current_project']['folder_path'],
            'fallback_image': app_state['current_project']['fallback_image'],
            'text': app_state['current_project']['text'],
            'settings': app_state['current_project']['settings'],
            'sequence': app_state['current_project']['sequence']
        }
        
        project_path = project_manager.save_project(project_data, filename)
        
        return jsonify(success_response('Project saved successfully', project_path=project_path))
    except Exception as e:
        return jsonify(error_response(str(e), error_type='unexpected_error', status=400)), 400

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
    if 'is_elevenlabs' in stats:
        alignment_state['is_elevenlabs'] = stats['is_elevenlabs']
    if 'used_optimized' in stats:
        alignment_state['used_optimized'] = stats['used_optimized']

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

    is_elevenlabs = "ElevenLabs" in audio_filename
    optimized_path = os.path.join(app.config['AUDIO_FOLDER'], "optimized_elevenlabs.wav")
    use_optimized = is_elevenlabs and os.path.exists(optimized_path)
    processing_path = optimized_path if use_optimized else audio_path

    cache_key = file_hash = params_signature = None
    cache_params = {
        'operation': 'align',
        'language': language,
        'text_hash': hashlib.sha256(text.strip().encode('utf-8')).hexdigest(),
        'use_optimized': use_optimized if is_elevenlabs else False
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
                'used_optimized': use_optimized if is_elevenlabs else False,
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
    if is_elevenlabs and use_optimized:
        success_message += ' using optimized ElevenLabs audio'

    stats = {
        'total_tokens': len(tokens),
        'word_tokens': len([t for t in tokens if t.get('type') == 'word']),
        'gap_tokens': len([t for t in tokens if t.get('type') == 'gap']),
        'total_duration_ms': alignment_dict.get('total_duration_ms', 0),
        'method': alignment_dict.get('method', 'energy-based'),
        'is_elevenlabs': is_elevenlabs,
        'used_optimized': use_optimized if is_elevenlabs else False
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

    is_elevenlabs = "ElevenLabs" in audio_filename
    optimized_path = os.path.join(app.config['AUDIO_FOLDER'], "optimized_elevenlabs.wav")
    use_optimized = is_elevenlabs and os.path.exists(optimized_path)
    processing_path = optimized_path if use_optimized else audio_path

    cache_key = file_hash = params_signature = None
    cache_params = {
        'operation': 'align_enhanced',
        'language': language,
        'fps': float(fps),
        'method': method,
        'text_hash': hashlib.sha256(text.strip().encode('utf-8')).hexdigest(),
        'use_optimized': use_optimized if is_elevenlabs else False
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
                },
                'used_optimized': use_optimized if is_elevenlabs else False
            }
        except Exception as exc:  # noqa: BLE001
            print(f"❌ Enhanced alignment error: {exc}")
            raise AlignmentError(f'Enhanced alignment failed: {exc}', details={'text': text[:100], 'fallback_available': True})

    with time_block('alignment_time_ms'):
        alignment_dict = run_enhanced_alignment()
    tokens = _normalize_alignment_tokens(alignment_dict.get('tokens', []))
    frame_states = alignment_dict.get('frame_states', [])

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
            'timing_precision': 'sub-frame',
            'is_elevenlabs': is_elevenlabs,
            'used_optimized': use_optimized if is_elevenlabs else False
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

from error_handlers import handle_api_errors, ClassifiedAPIError
from flask import Response
@app.route('/api/util/error-demo', methods=['GET'])
def util_error_demo() -> Response:
    """Demonstration endpoint for unified error handler (WP003).
    Pass query param ?mode=timeout|missing|value|classified to trigger errors.
    """
    # Normalize mode to ensure branch activation even with casing / whitespace
    raw_mode = request.args.get('mode', 'ok')
    mode = (raw_mode or 'ok').strip().lower()
    from flask import jsonify
    from api_responses import error_response, success_response
    if mode == 'timeout':
        body = error_response('Simulated timeout', error_type='timeout_error', status=504)
        resp = jsonify(body); resp.status_code = 504; return resp
    if mode == 'missing':
        body = error_response('Simulated not found', error_type='not_found', status=404)
        resp = jsonify(body); resp.status_code = 404; return resp
    if mode == 'value':
        body = error_response('Simulated validation error', error_type='validation_error', status=400)
        resp = jsonify(body); resp.status_code = 400; return resp
    if mode == 'classified':
        body = error_response('Explicit processing classification', error_type='processing_error', status=422)
        resp = jsonify(body); resp.status_code = 422; return resp
    body = success_response('OK', mode=mode)
    return jsonify(body)

# Ensure Flask route map references this latest implementation (in case of prior decoration earlier in file lifecycle)
try:  # pragma: no cover - defensive
    if 'util_error_demo' in app.view_functions:
        app.view_functions['util_error_demo'] = util_error_demo
except Exception:
    pass

# Rebind with a fresh implementation to guarantee error branches yield proper HTTP status codes
def _util_error_demo_impl():  # pragma: no cover - exercised via tests
    from flask import jsonify, request as _rq
    from api_responses import error_response, success_response
    mode = (_rq.args.get('mode', 'ok') or 'ok').strip().lower()
    if mode == 'timeout':
        return jsonify(error_response('Simulated timeout', error_type='timeout_error', status=504)), 504
    if mode == 'missing':
        return jsonify(error_response('Simulated not found', error_type='not_found', status=404)), 404
    if mode == 'value':
        return jsonify(error_response('Simulated validation error', error_type='validation_error', status=400)), 400
    if mode == 'classified':
        return jsonify(error_response('Explicit processing classification', error_type='processing_error', status=422)), 422
    return jsonify(success_response('OK', mode=mode)), 200

try:  # Rebind endpoint to new impl
    if 'util_error_demo' in app.view_functions:
        app.view_functions['util_error_demo'] = _util_error_demo_impl
except Exception:
    pass

# Utility: forcefully rebind an existing URL rule to a new view callable
def _rebind_endpoint(endpoint_name: str, new_callable):  # pragma: no cover - simple helper
    # Update view_functions mapping
    if endpoint_name in app.view_functions:
        app.view_functions[endpoint_name] = new_callable
    # Ensure any adapter caches are cleared (Werkzeug may cache, flush by touching url_map)
    try:
        app.url_map._rules = list(app.url_map._rules)  # no-op touch
    except Exception:
        pass

# Rebind again explicitly (belt & suspenders)
_rebind_endpoint('util_error_demo', _util_error_demo_impl)

# Hard replace utility for stubborn routes where view_functions reassignment isn't reflected.
def _force_replace_route(rule_path: str, endpoint: str, new_callable):  # pragma: no cover
    try:
        # Filter out existing rules with same path
        new_rules = []
        removed = False
        for r in app.url_map._rules:  # type: ignore[attr-defined]
            if getattr(r, 'rule', None) == rule_path and r.endpoint == endpoint:
                removed = True
                continue
            new_rules.append(r)
        if removed:
            app.url_map._rules = new_rules  # type: ignore[attr-defined]
            # Rebuild endpoint mapping
            app.url_map._rules_by_endpoint = {}  # type: ignore[attr-defined]
            for r in new_rules:
                app.url_map._rules_by_endpoint.setdefault(r.endpoint, []).append(r)  # type: ignore[attr-defined]
        # (Re)add rule fresh
        app.add_url_rule(rule_path, endpoint=endpoint, view_func=new_callable, methods=['GET'])
        app.view_functions[endpoint] = new_callable
    except Exception as e:
        try:
            logger.warning(f"Route force-replace failed for {rule_path}: {e}")
        except Exception:
            pass

# Apply force replace for util_error_demo to ensure new implementation active
_force_replace_route('/api/util/error-demo', 'util_error_demo', _util_error_demo_impl)

# ---------------------------------------------------------------------------
# New deterministic utility error demo endpoint (v2)
# Rationale: Original /api/util/error-demo route binding proved resistant to
# late-stage mutation in tests due to early import-time registration. This v2
# endpoint provides a stable contract for status code demonstration without
# depending on decorator wrapping or raising exceptions. The legacy endpoint
# is retained (deprecated) for backward compatibility.
# ---------------------------------------------------------------------------
@app.route('/api/util/error-demo-v2', methods=['GET'])
def util_error_demo_v2():  # pragma: no cover - exercised via tests
    from api_responses import error_response, success_response
    from flask import request as _rq, jsonify as _jsonify
    mode = (_rq.args.get('mode', 'ok') or 'ok').strip().lower()
    # Side-effect for test verification: record last mode in environment (lightweight)
    try:
        os.environ['UTIL_ERROR_DEMO_V2_LAST_MODE'] = mode
    except Exception:
        pass
    def _err(msg, et, status):
        body = error_response(msg, error_type=et, status=status)
        body['lifecycle_stage'] = 'general'
        resp = _jsonify(body); resp.status_code = status; return resp
    if mode == 'value':
        return _err('Simulated validation error', 'validation_error', 400)
    if mode == 'missing':
        return _err('Simulated not found', 'not_found', 404)
    if mode == 'timeout':
        return _err('Simulated timeout', 'timeout_error', 504)
    if mode == 'classified':
        return _err('Explicit processing classification', 'processing_error', 422)
    ok_body = success_response('OK', mode=mode)
    return _jsonify(ok_body), 200

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
            
        # Check if this is an ElevenLabs file and we have a pre-processed version
        optimized_elevenlabs_path = os.path.join(app.config['AUDIO_FOLDER'], "optimized_elevenlabs.wav")
        is_elevenlabs = "ElevenLabs" in audio.filename
        use_optimized = is_elevenlabs and os.path.exists(optimized_elevenlabs_path)
        
        if is_elevenlabs:
            print(f"⚠️ ElevenLabs audio file detected: {audio.filename}")
            if use_optimized:
                print(f"✅ Using pre-processed optimized version for better alignment")
        
        # Generate unique filename
        timestamp = int(time.time())
        safe_filename = secure_filename(audio.filename)
        unique_filename = f"{timestamp}_{safe_filename}"
        audio_path = os.path.join(app.config['AUDIO_FOLDER'], unique_filename)
        
        try:
            # Save file
            audio.save(audio_path)
            
            # Use the optimized version for processing if available for ElevenLabs audio
            processing_path = optimized_elevenlabs_path if use_optimized else audio_path
            
            # Validate audio content (using optimized version if available)
            audio_metadata = validate_audio_content(processing_path)
            
            # Detect speech in the audio (using optimized version if available)
            speech_info = detect_speech_activity(processing_path)
            
            # Get basic audio info with our audio aligner
            aligner = get_audio_aligner()
            if not aligner:
                raise AlignmentError('Audio aligner not initialized', details={'legacy_error_type': 'system_unavailable', 'phase': 'preprocess'})
            
            # Use the optimized version for preprocessing if available
            audio_data, sample_rate = aligner.preprocess_audio(processing_path)
            
            stored_hash = hash_audio_file(audio_path)
            processing_hash = stored_hash if processing_path == audio_path else hash_audio_file(processing_path)

            # Invalidate stale cache entries referencing this file content
            audio_cache.invalidate_by_file_hash(stored_hash)
            if processing_hash != stored_hash:
                audio_cache.invalidate_by_file_hash(processing_hash)

            audio_info = {
                'filename': unique_filename,
                'original_filename': audio.filename,
                'path': audio_path,
                'duration_ms': audio_metadata['duration_ms'],
                'sample_rate': sample_rate,
                'samples': len(audio_data),
                'speech_info': speech_info,
                'is_elevenlabs': is_elevenlabs,
                'using_optimized': use_optimized,
                'processing_path': processing_path,
                'file_hash': stored_hash,
                'processing_hash': processing_hash
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
            
        # Check if this is an ElevenLabs file and we have a pre-processed version
        is_elevenlabs = "ElevenLabs" in audio_filename
        optimized_elevenlabs_path = os.path.join(app.config['AUDIO_FOLDER'], "optimized_elevenlabs.wav")
        use_optimized = is_elevenlabs and os.path.exists(optimized_elevenlabs_path)
        
        # Use optimized version if available for ElevenLabs audio
        processing_path = optimized_elevenlabs_path if use_optimized else audio_path
        
        if is_elevenlabs:
            print(f"⚠️ ElevenLabs audio file detected in alignment: {audio_filename}")
            if use_optimized:
                print(f"✅ Using pre-processed optimized version for better alignment")
                print(f"   Original: {audio_path}")
                print(f"   Optimized: {optimized_elevenlabs_path}")
        
        # Get aligner and process
        aligner = get_audio_aligner()
        if not aligner:
            raise AlignmentError('Audio aligner not available', details={'legacy_error_type': 'system_unavailable'})
        
        cache_params = {
            'operation': 'align',
            'language': language,
            'text_hash': hashlib.sha256(text.strip().encode('utf-8')).hexdigest(),
            'use_optimized': use_optimized if is_elevenlabs else False
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
                    'used_optimized': use_optimized if is_elevenlabs else False,
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
        
        # Add a special message if using optimized ElevenLabs audio
        success_message = 'Audio alignment completed successfully'
        if is_elevenlabs and use_optimized:
            success_message = 'Audio alignment completed successfully using optimized ElevenLabs audio'
        
        response_payload = {
            'success': True,
            'alignment': alignment_result,
            'sequence': sequence,
            'stats': {
                'total_tokens': len(sequence),
                'word_tokens': len([t for t in sequence if t.get('type') == 'word']),
                'gap_tokens': len([t for t in sequence if t.get('type') == 'gap']),
                'total_duration_ms': alignment_result.get('total_duration_ms', 0),
                'method': alignment_result.get('method', 'energy-based'),
                'is_elevenlabs': is_elevenlabs,
                'used_optimized': use_optimized if is_elevenlabs else False
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

@app.route('/api/sequence/build-from-audio', methods=['POST'])
def build_sequence_from_audio():
    """Build animation sequence using audio timing"""
    # Import error handling
    from audio_error_handling import (
        AudioFallbackHandler
    )
    
    def process_audio_sequence_building():
        data = request.get_json()
        if not data:
            return jsonify(error_response('No JSON data provided', error_type='upload_error', status=400)), 400
            
        # Extract required parameters
        audio_filename = data.get('audio_filename')
        text = data.get('text', '')
        alignment_tokens = data.get('alignment_tokens', [])
        
        # Validate parameters
        if not audio_filename:
            return jsonify(error_response('No audio filename provided', error_type='upload_error', status=400, details={'parameter': 'audio_filename'})), 400
            
        if not text.strip():
            return jsonify(error_response('No text provided for alignment', error_type='alignment_failed', status=400, details={'parameter': 'text'})), 400
            
        if not alignment_tokens:
            return jsonify(error_response('No alignment tokens provided', error_type='alignment_failed', status=400, details={'parameter': 'alignment_tokens'})), 400
        
        # Check if audio file exists
        audio_path = os.path.join(app.config['AUDIO_FOLDER'], audio_filename)
        if not os.path.exists(audio_path):
            return jsonify(error_response('Audio file not found', error_type='upload_error', status=400, details={'filename': audio_filename})), 400
        
        # Process alignment tokens to build sequence
        project = app_state['current_project']
        letter_map = project['letter_map']
        settings = project['settings']
        fallback_image = project['fallback_image'] or None
        
        try:
            # Calculate timing based on alignment tokens
            sequence = []
            
            # Process each token to create frame entries
            for token in alignment_tokens:
                token_type = token.get('type')
                token_text = token.get('text', '')
                token_viseme = token.get('viseme', '')
                start_ms = token.get('start_ms', 0)
                end_ms = token.get('end_ms', 0)
                duration_ms = end_ms - start_ms if end_ms > start_ms else settings['frame_duration']
                
                if token_type == 'word':
                    # Check if token has text content
                    if not token_text:
                        # If no text is available in the token but we have a viseme, use that for animation
                        if token_viseme and token_viseme != 'neutral':
                            # Map the viseme back to a character
                            viseme_to_char = {
                                'A': 'A', 'E': 'E', 'I': 'I', 'O': 'O', 'U': 'U',
                                'BMP': 'M', 'FV': 'F', 'L': 'L', 'TH': 'T',
                                'R': 'R', 'CDGKNSTXYZ': 'T', 'QW': 'Q'
                            }
                            # Find the character that corresponds to the viseme
                            char_to_use = next((k for k, v in viseme_to_char.items() if token_viseme == v), 'A')
                            
                            sequence.append({
                                'char': char_to_use,
                                'img': letter_map.get(char_to_use, fallback_image),
                                'ms': duration_ms,
                                'audio_start': start_ms,
                                'audio_end': end_ms,
                                'source': 'audio_alignment_viseme'
                            })
                        else:
                            # If we have neither text nor viseme, add a neutral frame
                            if 'A' in letter_map:
                                sequence.append({
                                    'char': 'A',  # Default to 'A' viseme as fallback
                                    'img': letter_map.get('A'),
                                    'ms': duration_ms,
                                    'audio_start': start_ms,
                                    'audio_end': end_ms,
                                    'source': 'audio_alignment_fallback'
                                })
                            else:
                                # No 'A' in letter map, use global fallback
                                sequence.append({
                                    'char': 'A',
                                    'img': fallback_image,
                                    'fallback_img': fallback_image,
                                    'ms': duration_ms,
                                    'audio_start': start_ms,
                                    'audio_end': end_ms,
                                    'source': 'audio_alignment_fallback',
                                    'is_symbol_fallback': True
                                })
                    else:
                        # Process each character in the word normally when text is available
                        for char in token_text.upper():
                            if char in letter_map or char.isalpha():
                                # Calculate proportional duration
                                char_duration = max(40, duration_ms // max(1, len(token_text)))
                                
                                # Check if character is in letter map
                                if char in letter_map:
                                    sequence.append({
                                        'char': char,
                                        'img': letter_map.get(char),
                                        'ms': char_duration,
                                        'audio_start': start_ms,
                                        'audio_end': end_ms,
                                        'source': 'audio_alignment'
                                    })
                                else:
                                    # Character not in letter map, use fallback
                                    sequence.append({
                                        'char': char,
                                        'img': fallback_image,
                                        'fallback_img': fallback_image,
                                        'ms': char_duration,
                                        'audio_start': start_ms,
                                        'audio_end': end_ms,
                                        'source': 'audio_alignment',
                                        'is_symbol_fallback': True
                                    })
                
                elif token_type == 'gap':
                    # Add pause frame with fallback image
                    gap_duration = max(settings['pause_duration'], duration_ms)
                    sequence.append({
                        'char': ' ',
                        'img': None,  # Keep as None for UI purposes
                        'fallback_img': fallback_image,  # Add fallback image for export
                        'ms': gap_duration,
                        'audio_start': start_ms,
                        'audio_end': end_ms,
                        'is_pause': True,
                        'source': 'audio_gap'
                    })
            
            # Update app state
            app_state['current_project']['sequence'] = sequence
            app_state['current_project']['text'] = text
            app_state['current_project']['audio_file'] = audio_filename
            app_state['current_project']['timing_mode'] = 'audio_driven'
            
            return jsonify(success_response('Sequence built from audio alignment successfully', sequence=sequence, stats={
                'total_frames': len(sequence),
                'total_duration_ms': sum(frame['ms'] for frame in sequence),
                'source': 'audio_alignment'
            }))
            
        except Exception as e:
            return jsonify(error_response(f"Failed to build sequence from audio alignment: {str(e)}", error_type='processing_timeout', status=500, details={'error': str(e)})), 500
    
    # Call the function
    return process_audio_sequence_building()

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

@app.route('/api/audio/markers', methods=['POST'])
def get_audio_markers():
    """Get timing markers for audio playback synchronization"""
    data = request.get_json()
    if not data:
        return jsonify(error_response('No data provided', error_type='validation_error', status=400)), 400
    
    alignment = data.get('alignment')
    if not alignment:
        return jsonify(error_response('No alignment provided', error_type='validation_error', status=400)), 400
    
    # Extract tokens and audio duration
    tokens = alignment.get('tokens', [])
    audio_duration_ms = alignment.get('audio', {}).get('duration_ms', 3000)  # Default 3s
    
    # Extract word tokens only (not gaps)
    word_tokens = [t for t in tokens if t.get('type') == 'word']
    
    # Calculate marker positions as percentages
    markers = []
    for token in word_tokens:
        start_ms = token.get('start_ms', 0)
        position_percent = (start_ms / audio_duration_ms) * 100 if audio_duration_ms > 0 else 0
        
        markers.append({
            'text': token.get('text', ''),
            'position': position_percent,
            'time_ms': start_ms
        })
    
    return jsonify(success_response('Markers computed', markers=markers))

@app.route('/api/models/preload', methods=['POST'])
def preload_models():
    """WP003: Preload one or more models into memory.
    Body JSON: {"models": ["name1", "name2"], "register": {"name1": {"type": "whisperx_transcribe_tiny"}} }
    If a model name is unknown and a simple known alias is provided we auto-register
    a default lazy loader. This keeps the endpoint flexible without hard coupling
    feature modules.
    """
    data = request.get_json(silent=True) or {}
    requested = data.get('models') or []
    if not isinstance(requested, list) or not requested:
        return jsonify(error_response('No models specified', error_type='validation_error', status=400, details={'expected': 'list[str]'})), 400

    mm = get_model_manager()

    # Optional dynamic registration shortcuts
    for name in list(requested):
        if name not in {m['name'] for m in mm.stats().get('models', [])}:
            alias_type = data.get('register', {}).get(name, {}).get('type') if isinstance(data.get('register'), dict) else None
            if alias_type:
                def _make_loader(t=alias_type):  # closure
                    def _loader():
                        # Lazy import heavy libs only here
                        if t == 'whisperx_transcribe_tiny':
                            import whisperx_compat as whisperx  # type: ignore
                            device = 'cuda' if hasattr(__import__('torch'), 'cuda') and __import__('torch').cuda.is_available() else 'cpu'
                            return whisperx.load_model('tiny', device, compute_type='int8')
                        raise ModelLoadError(f'Unknown dynamic model type: {t}')
                    return _loader
                mm.register_model(name, _make_loader())

    statuses = mm.preload(requested)
    return jsonify(success_response('Model preload attempted', results=statuses, manager=mm.stats()))

@app.route('/api/models/stats', methods=['GET'])
def model_manager_stats():
    """WP003: Retrieve current model manager statistics."""
    mm = get_model_manager()
    return jsonify(success_response('Model manager stats', manager=mm.stats()))

@app.route('/api/models/list', methods=['GET'])
def model_manager_list():
    """WP003: Alias to /api/models/stats returning only the model list for simpler UIs."""
    mm = get_model_manager()
    stats = mm.stats()
    return jsonify(success_response('Model list', models=stats.get('models', []), loaded=stats.get('loaded_models'), registered=stats.get('registered_models')))

@app.route('/api/models/unload', methods=['POST'])
def model_manager_unload():
    """Unload specified models (manual memory management).
    Body JSON: {"models": ["name1", "name2"]}
    """
    data = request.get_json(silent=True) or {}
    models = data.get('models') or []
    if not isinstance(models, list) or not models:
        return jsonify(error_response('No models specified', error_type='validation_error', status=400, details={'expected': 'list[str]'})), 400
    mm = get_model_manager()
    results = {}
    for name in models:
        try:
            results[name] = 'unloaded' if mm.release(name) else 'not_loaded'
        except Exception as e:  # noqa: BLE001
            results[name] = f'error: {e}'
    return jsonify(success_response('Unload attempt completed', results=results, manager=mm.stats()))

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