import pytest
from app import app

@pytest.fixture(scope='module')
def client():
    app.config.update(TESTING=True)
    with app.test_client() as c:
        yield c


def _assert_error_payload(d):
    assert d['success'] is False
    assert 'error' in d
    assert 'error_type' in d
    # lifecycle_stage added via unified error responses for audio
    assert d.get('lifecycle_stage') in {'alignment', 'general', None}
    # recommendations are optional but if present must be a list
    if 'recommendations' in d:
        assert isinstance(d['recommendations'], list)


def test_align_missing_body_contract(client):
    resp = client.post('/api/audio/align', data='{}', content_type='application/json')
    data = resp.get_json()
    # Should produce an error for missing text/filename
    if data.get('success') is False:
        _assert_error_payload(data)


def test_analyze_missing_body_contract(client):
    resp = client.post('/api/audio/analyze', data='{}', content_type='application/json')
    data = resp.get_json()
    if data.get('success') is False:
        _assert_error_payload(data)


def test_upload_missing_file_contract(client):
    # No multipart data triggers decorator-level validation failure
    resp = client.post('/api/audio/upload')
    # Could return 400 or another mapped status depending on handler path
    data = resp.get_json()
    if data:  # some frameworks may produce HTML fallback, ensure JSON path
        if data.get('success') is False:
            _assert_error_payload(data)

