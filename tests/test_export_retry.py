import pytest, time

@pytest.fixture()
def client():
    from app import app
    app.config.update(TESTING=True)
    # Provide a minimal sequence so export can proceed quickly
    state = app.config['app_state']
    state['current_project']['sequence'] = [{'img': None, 'char':'A', 'ms':100}]
    with app.test_client() as c:
        yield c

def test_export_retry_flow(client):
    # Start export
    start_resp = client.post('/api/export/video', json={'filename': 'retry_test.mp4'})
    assert start_resp.status_code == 200
    start_data = start_resp.get_json(); task_id = start_data['task_id']
    # Poll status until terminal or timeout
    deadline = time.time()+5
    status = None
    while time.time() < deadline:
        r = client.get(f'/api/export/status/{task_id}')
        assert r.status_code in (200, 404)
        if r.status_code == 404:
            break
        data = r.get_json(); status = data['task']['status']
        if status in ('completed','error'): break
        time.sleep(0.1)
    assert status in ('completed','error')
    # Force mark error to exercise retry path if completed
    if status == 'completed':
        from app import app as flask_app
        flask_app.config['app_state']['export_tasks'][task_id]['status'] = 'error'
    retry_resp = client.post(f'/api/export/retry/{task_id}')
    assert retry_resp.status_code == 200
    retry_data = retry_resp.get_json(); new_task = retry_data.get('new_task_id')
    assert new_task and new_task != task_id
    from app import app as flask_app
    original_task = flask_app.config['app_state']['export_tasks'][task_id]
    new_task_meta = flask_app.config['app_state']['export_tasks'][new_task]
    # Parameter fidelity assertions
    for key in ('quality_preset','crf','preset','fps'):
        assert original_task.get(key) == new_task_meta.get(key)
