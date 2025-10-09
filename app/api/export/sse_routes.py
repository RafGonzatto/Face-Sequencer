from flask import Blueprint, jsonify, Response, stream_with_context
from app.core.utils.api_responses import error_response
from app.core.utils.sse_manager import sse_manager
import json, time

export_sse_bp = Blueprint('export_sse', __name__)

@export_sse_bp.route('/api/sse/export-progress/<task_id>', methods=['GET'])
def export_progress_stream(task_id):
    """SSE endpoint for streaming export progress."""
    try:
        # Get app state from current_app
        from flask import current_app
        app_state = current_app.config.get('app_state', {})
        
        # Verify the task exists
        if task_id not in app_state.get('export_tasks', {}):
            return jsonify(error_response('Task not found', error_type='not_found', status=404)), 404
        
        def event_stream():
            """Generate SSE event stream."""
            # Get app state from current_app
            from flask import current_app
            from queue import Empty
            app_state = current_app.config.get('app_state', {})
            
            # Create a client-specific queue for this connection
            client_queue = sse_manager.add_client(task_id, 'export_progress')
            
            # Send initial message with current status
            task = app_state.get('export_tasks', {}).get(task_id, {'status': 'unknown', 'progress': 0, 'message': 'Initializing', 'error': None})
            initial_data = {
                'status': task.get('status', 'unknown'),
                'progress': task.get('progress', 0),
                'message': task.get('message', 'Initializing'),
                'error': task.get('error', None),
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
                    from flask import current_app
                    app_state = current_app.config.get('app_state', {})
                    current_task = app_state.get('export_tasks', {}).get(task_id, {})
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