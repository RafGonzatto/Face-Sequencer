"""Test that export status includes enriched metadata fields."""
import time, pytest

@pytest.fixture()
def client():
    from app import app
    app.config.update(TESTING=True)
    state = app.config['app_state']
    state['current_project']['sequence'] = [{'img': None,'char':'A','ms':100}]
    with app.test_client() as c:
        yield c

def test_export_status_metadata_fields(client):
    start = client.post('/api/export/video', json={'filename':'meta_test.mp4','quality':'high'})
    assert start.status_code == 200
    task_id = start.get_json()['task_id']
    required_meta = {'quality_preset','crf','preset','fps','started_at','frame_count','encode_duration_ms'}
    deadline = time.time()+5
    last = None
    while time.time() < deadline:
        r = client.get(f'/api/export/status/{task_id}')
        assert r.status_code == 200
        data = r.get_json()['task']
        last = data
        if data['status'] in ('completed','error'): break
        time.sleep(0.1)
    assert last is not None
    missing = required_meta - set(last.keys())
    assert not missing, f"Missing metadata keys: {missing}"
    # encode_duration_ms may be None if error; ensure key present
    assert 'encode_duration_ms' in last
