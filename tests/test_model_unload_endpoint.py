import pytest
from app import app

@pytest.fixture(scope="module")
def client():
    app.config.update(TESTING=True)
    with app.test_client() as c:
        yield c

def test_unload_requires_models_array(client):
    resp = client.post('/api/models/unload', json={})
    assert resp.status_code == 400
    data = resp.get_json()
    assert data['success'] is False
    assert data.get('error_type') in {'validation_error', 'alignment_error', 'model_error'}
    assert 'No models specified' in data.get('error', '')


def test_unload_unknown_model(client):
    resp = client.post('/api/models/unload', json={'models': ['nonexistent_model_123']})
    assert resp.status_code == 200  # Endpoint returns 200 with per-model status strings
    data = resp.get_json()
    assert data['success'] is True
    results = data.get('results', {})
    assert 'nonexistent_model_123' in results
    # Status should indicate not_loaded (since not registered)
    assert results['nonexistent_model_123'] in {'not_loaded', 'unloaded'}


def test_unload_happy_path(client):
    # Register and preload a lightweight model through manager indirectly
    from model_manager import get_model_manager
    mm = get_model_manager()
    mm.register_model('tmp_unload_model', lambda: {'value': 1}, size_estimate=1024)
    mm.preload(['tmp_unload_model'])
    assert mm.has_model('tmp_unload_model')

    resp = client.post('/api/models/unload', json={'models': ['tmp_unload_model']})
    assert resp.status_code == 200
    data = resp.get_json()
    results = data.get('results', {})
    assert results.get('tmp_unload_model') in {'unloaded', 'not_loaded'}

    # Ensure manager reflects unload
    mm_stats = mm.stats()
    srch = [m for m in mm_stats['models'] if m['name'] == 'tmp_unload_model']
    if srch:
        # If listed ensure not loaded
        assert srch[0]['loaded'] is False
