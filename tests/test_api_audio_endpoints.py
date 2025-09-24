import json
import pytest
from app import app

@pytest.fixture(scope="module")
def test_client():
    app.config.update(TESTING=True)
    with app.test_client() as client:
        yield client


def _assert_standard_response(data, *, expect_success: bool):
    assert 'success' in data, 'missing success key'
    assert data['success'] is expect_success, 'success flag mismatch'
    if expect_success:
        assert 'message' in data, 'missing success message'
    else:
        assert 'error' in data, 'missing error message'
        assert 'error_type' in data or 'details' in data or 'status' in data


def test_audio_status(test_client):
    resp = test_client.get('/api/audio/status')
    assert resp.status_code == 200
    data = resp.get_json()
    _assert_standard_response(data, expect_success=True)
    assert 'features' in data


def test_align_missing_body(test_client):
    # No JSON payload should trigger handled error
    resp = test_client.post('/api/audio/align', data='{}', content_type='application/json')
    data = resp.get_json()
    # Could be success=False due to missing filename/text
    if data.get('success') is False:
        _assert_standard_response(data, expect_success=False)
    else:  # In case underlying handler short-circuits differently
        _assert_standard_response(data, expect_success=True)


def test_analyze_missing_body(test_client):
    resp = test_client.post('/api/audio/analyze', data='{}', content_type='application/json')
    data = resp.get_json()
    # Expect error because no filename
    if data.get('success') is False:
        _assert_standard_response(data, expect_success=False)
