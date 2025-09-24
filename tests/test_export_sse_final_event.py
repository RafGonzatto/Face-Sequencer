"""Test that the final SSE event for an export contains encode_duration_ms field."""
import time, json, pytest

@pytest.fixture()
def app_client_and_state():
    from app import app
    app.config.update(TESTING=True)
    state = app.config['app_state']
    state['current_project']['sequence'] = [{'img': None,'char':'A','ms':100}]
    yield app, state, app.test_client()

def test_sse_final_event_contains_encode_duration(app_client_and_state):
    app, state, client = app_client_and_state
    with client:
        start = client.post('/api/export/video', json={'filename':'sse_meta.mp4'})
        assert start.status_code == 200
        task_id = start.get_json()['task_id']
        # Poll until terminal
        deadline = time.time()+5
        while time.time() < deadline:
            resp = client.get(f'/api/export/status/{task_id}')
            if resp.status_code == 404:
                break
            data = resp.get_json()['task']
            if data['status'] in ('completed','error'): break
            time.sleep(0.1)
        # Access SSE manager history directly
        from sse_manager import sse_manager
        history = sse_manager._event_history.get(task_id, {}).get('export_progress', [])  # type: ignore[attr-defined]
        assert history, 'No SSE history captured'
        # Parse last event JSON
        last_event_raw = history[-1]
        evt = json.loads(last_event_raw)
        assert evt['event'] == 'export_progress'
        payload = evt['data']
        assert 'encode_duration_ms' in payload, f"encode_duration_ms missing from final event payload: {payload}" 
        # Value can be None if export failed early; just ensure key presence.