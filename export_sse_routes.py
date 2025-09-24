@app.route('/api/sse/export-progress/<task_id>', methods=['GET'])
def export_progress_stream(task_id):
    """SSE endpoint for streaming export progress."""
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