import pytest

@pytest.fixture(scope='module')
def client():
    from app import app
    app.config.update(TESTING=True)
    with app.test_client() as c:
        yield c

def test_preload_requires_models_array(client):
    resp = client.post('/api/models/preload', json={})
    assert resp.status_code == 400
    data = resp.get_json(); assert data['error_type'] == 'validation_error'


def test_preload_dynamic_registration_and_stats(client):
    # Use a fake dynamic registration alias that will fail gracefully
    # We expect unknown dynamic model type to surface as error in results but not crash endpoint
    resp = client.post('/api/models/preload', json={'models': ['fake_model_a'], 'register': {'fake_model_a': {'type': 'unknown_type'}}})
    # Even with dynamic attempt, the endpoint should succeed (returns per-model status mapping)
    data = resp.get_json(); assert data['success'] is True
    assert 'results' in data

    # Stats endpoint should be available
    stats_resp = client.get('/api/models/stats')
    assert stats_resp.status_code == 200
    stats_data = stats_resp.get_json(); assert stats_data['success'] is True
    assert 'manager' in stats_data

    # List endpoint should supply model list
    list_resp = client.get('/api/models/list')
    assert list_resp.status_code == 200
    list_data = list_resp.get_json(); assert list_data['success'] is True
    assert 'models' in list_data

