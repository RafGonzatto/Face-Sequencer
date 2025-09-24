"""Export-related endpoints (video & JSON) plus SSE progress streaming."""
from __future__ import annotations
from flask import Blueprint, request, jsonify, send_file, Response, stream_with_context
from api_responses import success_response, error_response
from metrics import record_timing
from sse_manager import sse_manager
import os, uuid, time, json, threading
from datetime import datetime
from pathlib import Path
from logger import get_logger
from lipanim_core_demo import export_json, export_mp4

export_bp = Blueprint('export', __name__)
logger = get_logger(__name__)

# Shared state dependency will still live in app.config['app_state'] injected at registration time

def _get_state(bp_app):
    return bp_app.config.get('app_state')

@export_bp.route('/api/export/json', methods=['POST'])
def export_sequence_json():
    from flask import current_app
    state = _get_state(current_app)
    data = request.get_json()
    filename = data.get('filename', 'sequence.json') if data else 'sequence.json'
    sequence = state['current_project']['sequence']
    if not sequence:
        return jsonify({'success': False, 'error': 'No sequence to export'}), 400
    export_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    export_json(sequence, export_path)
    return send_file(export_path, as_attachment=True, download_name=filename)

@export_bp.route('/api/export/video', methods=['POST'])
def export_sequence_video():
    from flask import current_app
    state = _get_state(current_app)
    data = request.get_json() or {}
    filename = data.get('filename', 'sequence.mp4')
    quality_preset = data.get('quality', 'medium')
    sequence = state['current_project']['sequence']
    settings = state['current_project']['settings']
    if not sequence:
        return jsonify(error_response('No sequence to export', error_type='empty_sequence', status=400)), 400
    task_id = str(uuid.uuid4())
    quality_settings = {
        'high': {'crf': 15, 'preset': 'slow'},
        'medium': {'crf': 20, 'preset': 'medium'},
        'fast': {'crf': 26, 'preset': 'fast'}
    }
    quality_config = quality_settings.get(quality_preset, quality_settings['medium'])
    export_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    os.makedirs(os.path.dirname(os.path.abspath(export_path)), exist_ok=True)
    state['export_tasks'][task_id] = {
        'status': 'pending','progress': 0,'filename': filename,'path': export_path,'error': None,'message': 'Preparing to export video','started_at': datetime.now(),
        'quality_preset': quality_preset,'crf': quality_config['crf'],'preset': quality_config['preset'],'fps': settings['fps']
    }
    def export_worker():
        try:
            state['export_tasks'][task_id]['status'] = 'processing'
            _t0 = time.perf_counter()
            def update_progress(progress, message=None):
                state['export_tasks'][task_id]['progress'] = progress
                if message:
                    state['export_tasks'][task_id]['message'] = message
                sse_manager.publish_event(task_id, 'export_progress', {
                    'status': state['export_tasks'][task_id]['status'],
                    'progress': progress,'message': state['export_tasks'][task_id]['message'],'error': state['export_tasks'][task_id]['error']
                })
                if progress < 0:
                    state['export_tasks'][task_id]['status'] = 'error'
                    state['export_tasks'][task_id]['error'] = message or 'Unknown error'
                    sse_manager.publish_event(task_id, 'export_progress', {
                        'status': 'error','progress': -1,'message': message or 'Unknown error','error': message or 'Unknown error'
                    })
            success = export_mp4(seq=sequence, path=export_path, fps=settings['fps'], crf=quality_config['crf'], preset=quality_config['preset'], progress_callback=update_progress)
            if success:
                state['export_tasks'][task_id]['status'] = 'completed'
                state['export_tasks'][task_id]['progress'] = 100
                state['export_tasks'][task_id]['message'] = 'Export completed successfully'
                try: record_timing('export_time_ms', (time.perf_counter()-_t0)*1000.0)
                except Exception: pass
                sse_manager.publish_event(task_id,'export_progress',{'status':'completed','progress':100,'message':'Export completed successfully','error':None})
            else:
                if state['export_tasks'][task_id]['status'] != 'error':
                    state['export_tasks'][task_id]['status'] = 'error'
                    state['export_tasks'][task_id]['error'] = 'Export failed'
                    sse_manager.publish_event(task_id,'export_progress',{'status':'error','progress':100,'message':'Export failed','error':'Export failed'})
        except Exception as e:  # noqa: BLE001
            state['export_tasks'][task_id]['status'] = 'error'
            state['export_tasks'][task_id]['error'] = str(e)
            sse_manager.publish_event(task_id,'export_progress',{'status':'error','progress':100,'message':f'Export error: {e}','error':str(e)})
    threading.Thread(target=export_worker, daemon=False).start()
    return jsonify(success_response('Export started', task_id=task_id))

@export_bp.route('/api/export/status/<task_id>', methods=['GET'])
def get_export_status(task_id):
    from flask import current_app
    state = _get_state(current_app)
    if task_id not in state['export_tasks']:
        return jsonify(error_response('Task not found', error_type='not_found', status=404)), 404
    return jsonify(success_response('Export status', task=state['export_tasks'][task_id]))

@export_bp.route('/api/export/retry/<task_id>', methods=['POST'])
def retry_export(task_id):
    from flask import current_app
    state = _get_state(current_app)
    if task_id not in state['export_tasks']:
        return jsonify(error_response('Task not found', error_type='not_found', status=404)), 404
    original = state['export_tasks'][task_id]
    if original['status'] != 'error':
        return jsonify(error_response('Can only retry failed exports', error_type='invalid_state', status=400)), 400
    # Perform real requeue: create a new task id and start export_worker again using same parameters
    new_task_id = str(uuid.uuid4())
    sequence = state['current_project']['sequence']
    settings = state['current_project']['settings']
    if not sequence:
        return jsonify(error_response('No sequence to export', error_type='empty_sequence', status=400)), 400
    state['export_tasks'][new_task_id] = {
        'status': 'pending','progress': 0,'filename': original['filename'],'path': original['path'],'error': None,'message': 'Retrying export','started_at': datetime.now(),
        'quality_preset': original.get('quality_preset'),'crf': original.get('crf'),'preset': original.get('preset'),'fps': original.get('fps', settings['fps'])
    }
    def retry_worker():
        try:
            state['export_tasks'][new_task_id]['status'] = 'processing'
            _t0 = time.perf_counter()
            def update_progress(progress, message=None):
                state['export_tasks'][new_task_id]['progress'] = progress
                if message:
                    state['export_tasks'][new_task_id]['message'] = message
                sse_manager.publish_event(new_task_id, 'export_progress', {
                    'status': state['export_tasks'][new_task_id]['status'],
                    'progress': progress,'message': state['export_tasks'][new_task_id]['message'],'error': state['export_tasks'][new_task_id]['error']
                })
                if progress < 0:
                    state['export_tasks'][new_task_id]['status'] = 'error'
                    state['export_tasks'][new_task_id]['error'] = message or 'Unknown error'
                    sse_manager.publish_event(new_task_id, 'export_progress', {
                        'status': 'error','progress': -1,'message': message or 'Unknown error','error': message or 'Unknown error'
                    })
            # Reuse original qualitative settings if present
            crf = state['export_tasks'][new_task_id].get('crf', 20)
            preset = state['export_tasks'][new_task_id].get('preset', 'medium')
            fps_local = state['export_tasks'][new_task_id].get('fps', settings['fps'])
            success = export_mp4(seq=sequence, path=original['path'], fps=fps_local, crf=crf, preset=preset, progress_callback=update_progress)
            if success:
                state['export_tasks'][new_task_id]['status'] = 'completed'
                state['export_tasks'][new_task_id]['progress'] = 100
                state['export_tasks'][new_task_id]['message'] = 'Export retry completed successfully'
                try: record_timing('export_time_ms', (time.perf_counter()-_t0)*1000.0)
                except Exception: pass
                sse_manager.publish_event(new_task_id,'export_progress',{'status':'completed','progress':100,'message':'Export retry completed successfully','error':None})
            else:
                if state['export_tasks'][new_task_id]['status'] != 'error':
                    state['export_tasks'][new_task_id]['status'] = 'error'
                    state['export_tasks'][new_task_id]['error'] = 'Export retry failed'
                    sse_manager.publish_event(new_task_id,'export_progress',{'status':'error','progress':100,'message':'Export retry failed','error':'Export retry failed'})
        except Exception as e:  # noqa: BLE001
            state['export_tasks'][new_task_id]['status'] = 'error'
            state['export_tasks'][new_task_id]['error'] = str(e)
            sse_manager.publish_event(new_task_id,'export_progress',{'status':'error','progress':100,'message':f'Export retry error: {e}','error':str(e)})
    threading.Thread(target=retry_worker, daemon=False).start()
    return jsonify(success_response('Retry started', original_task_id=task_id, new_task_id=new_task_id))

@export_bp.route('/api/sse/export-progress/<task_id>', methods=['GET'])
def export_progress_stream(task_id):
    from flask import current_app
    state = _get_state(current_app)
    if task_id not in state['export_tasks']:
        return jsonify(error_response('Task not found', error_type='not_found', status=404)), 404
    def event_stream():
        from queue import Empty
        client_queue = sse_manager.add_client(task_id, 'export_progress')
        initial_task = state['export_tasks'][task_id]
        yield f"data: {json.dumps({'status': initial_task['status'],'progress': initial_task['progress'],'message': initial_task['message'],'error': initial_task['error'],'initial': True})}\n\n"
        try:
            while True:
                try:
                    message = client_queue.get(timeout=0.5)
                    yield f"data: {message}\n\n"
                except Empty:
                    yield ": keep-alive\n\n"
                current_task = state['export_tasks'].get(task_id, {})
                if current_task.get('status') in ['completed','error']:
                    time.sleep(1)
                    yield ": task-complete\n\n"
                    break
        finally:
            sse_manager.remove_client(task_id, 'export_progress', client_queue)
    return Response(stream_with_context(event_stream()), mimetype='text/event-stream', headers={'Cache-Control':'no-cache','X-Accel-Buffering':'no','Connection':'keep-alive'})

__all__ = ['export_bp']
