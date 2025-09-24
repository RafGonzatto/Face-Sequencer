"""WP006: Tests for /api/health endpoint and basic metrics shape."""
from __future__ import annotations

import pytest
from app import app


@pytest.fixture(scope='module')
def client():
    app.config.update(TESTING=True)
    with app.test_client() as c:
        yield c


def test_health_basic_structure(client):
    resp = client.get('/api/health')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get('success') is True
    assert 'components' in data and isinstance(data['components'], dict)
    assert 'metrics' in data and isinstance(data['metrics'], dict)
    assert 'requests' in data['metrics']


def test_metrics_increment_request_count(client):
    # Capture initial count
    initial = client.get('/api/health').get_json()['metrics']['requests']['count']
    client.get('/api/audio/status')
    after = client.get('/api/health').get_json()['metrics']['requests']['count']
    assert after >= initial + 1
