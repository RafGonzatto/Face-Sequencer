import json
import yaml
import pytest
from app import app

with open('openapi.yaml', 'r', encoding='utf-8') as f:
    SPEC = yaml.safe_load(f)

@pytest.fixture(scope='module')
def client():
    app.config.update(TESTING=True)
    with app.test_client() as c:
        yield c

# Utility to check standard envelope quickly
def _assert_standard_envelope(data):
    assert 'success' in data
    if data['success']:
        assert 'message' in data
    else:
        assert 'error' in data

@pytest.mark.parametrize('path,method', [
    ('/api/audio/status','get'),
    ('/api/audio/align','post'),
    ('/api/audio/analyze','post'),
])
def test_paths_present_in_spec(path, method):
    paths = SPEC.get('paths', {})
    assert path in paths, f'{path} missing from spec'
    assert method in paths[path], f'{method} missing for {path}'


def test_status_endpoint_contract(client):
    resp = client.get('/api/audio/status')
    assert resp.status_code == 200
    data = resp.get_json()
    _assert_standard_envelope(data)
    # Basic contract: features object present
    assert 'features' in data


def test_alignment_contract_error_shape(client):
    # Missing payload should yield standardized error or handled response
    resp = client.post('/api/audio/align', json={})
    data = resp.get_json()
    _assert_standard_envelope(data)
    if not data['success']:
        # Allowed keys from spec envelope
        assert 'error' in data


def test_analysis_contract_error_shape(client):
    resp = client.post('/api/audio/analyze', json={})
    data = resp.get_json()
    _assert_standard_envelope(data)
    if not data['success']:
        assert 'error' in data
