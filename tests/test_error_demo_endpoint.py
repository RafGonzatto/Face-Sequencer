def test_error_demo_validation(client):
    r = client.get('/api/util/error-demo-v2?mode=value')
    assert r.status_code == 400
    data = r.get_json(); assert data['error_type'] == 'validation_error'
    # Unified error responses include lifecycle_stage (may be None or category)
    assert 'lifecycle_stage' in data

def test_error_demo_not_found(client):
    r = client.get('/api/util/error-demo-v2?mode=missing')
    assert r.status_code == 404
    data = r.get_json(); assert 'lifecycle_stage' in data

def test_error_demo_timeout(client):
    r = client.get('/api/util/error-demo-v2?mode=timeout')
    assert r.status_code == 504
    data = r.get_json(); assert 'lifecycle_stage' in data

def test_error_demo_ok(client):
    r = client.get('/api/util/error-demo-v2')
    assert r.status_code == 200
    data = r.get_json(); assert data.get('success') is True
