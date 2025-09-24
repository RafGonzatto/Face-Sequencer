import pytest

@pytest.mark.order(10)
def test_dynamic_model_alias_whisperx_tiny(client):
    # Attempt to preload a dynamic alias; in test mode underlying load may be skipped or fail gracefully
    payload = {
        'models': ['my_tiny_alias'],
        'register': {
            'my_tiny_alias': {'type': 'whisperx_transcribe_tiny'}
        }
    }
    resp = client.post('/api/models/preload', json=payload)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success'] is True
    results = data.get('results', {})
    # Result could be 'loaded' or an error if dependency missing; both acceptable but we verify registration appears in stats
    assert 'my_tiny_alias' in results
    stats_resp = client.get('/api/models/list')
    assert stats_resp.status_code == 200
    stats_data = stats_resp.get_json()
    model_names = [m['name'] for m in stats_data.get('models', [])]
    assert 'my_tiny_alias' in model_names
