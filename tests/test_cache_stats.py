# WP002 test: verify /api/cache/stats endpoint returns expected fields

def test_cache_stats_endpoint(client):
    resp = client.get('/api/cache/stats')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success'] is True
    payload = data['data']
    # Required fields
    for field in ['entries','max_entries','ttl_seconds','hits','misses','hit_rate','evictions','sets','approx_value_bytes']:
        assert field in payload, f"Missing field {field} in cache stats response"
