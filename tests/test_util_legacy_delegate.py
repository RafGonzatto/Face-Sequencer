import pytest

@pytest.fixture()
def client():
    from app import app as flask_app
    with flask_app.test_client() as c:
        yield c

def test_legacy_error_demo_delegates_validation(client):
    r = client.get('/api/util/error-demo?mode=value')
    assert r.status_code == 400
    data = r.get_json(); assert data['error_type'] == 'validation_error'


def test_legacy_error_demo_delegates_ok(client):
    r = client.get('/api/util/error-demo')
    assert r.status_code == 200
    data = r.get_json(); assert data.get('success') is True
