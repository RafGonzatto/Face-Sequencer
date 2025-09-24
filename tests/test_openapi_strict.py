"""Strict JSON schema validation tests.

These tests validate that selected live endpoint responses conform to
schemas declared in openapi.yaml. Only lightweight endpoints are tested
to keep CI fast; heavy audio alignment endpoints skipped when FAST_TESTS
environment variable is set.
"""
from __future__ import annotations

import os
import json
import typing as t

import yaml
import jsonschema
import pytest
from app import app

with open('openapi.yaml', 'r', encoding='utf-8') as f:
    SPEC = yaml.safe_load(f)


def _resolve_ref(ref: str):
    assert ref.startswith('#/components/schemas/'), f"Unsupported $ref {ref}"
    name = ref.split('/')[-1]
    return SPEC['components']['schemas'][name]


def _expand_schema(schema: dict) -> dict:
    """Recursively expand $ref in a shallow way (no cycles expected)."""
    if '$ref' in schema:
        resolved = _resolve_ref(schema['$ref']).copy()
        # Merge extra keys alongside $ref (OpenAPI allOf not handled here)
        for k, v in schema.items():
            if k != '$ref':
                resolved[k] = v
        return _expand_schema(resolved)
    if 'allOf' in schema:
        merged: dict = {'type': 'object', 'properties': {}, 'required': []}
        for part in schema['allOf']:
            exp = _expand_schema(part)
            if exp.get('type') == 'object':
                merged['properties'].update(exp.get('properties', {}))
                if 'required' in exp:
                    merged['required'].extend(exp['required'])
            else:
                # Fallback simple merge
                for k, v in exp.items():
                    if k not in merged:
                        merged[k] = v
        return merged
    # Recurse into properties / items
    if 'properties' in schema:
        for k, v in list(schema['properties'].items()):
            schema['properties'][k] = _expand_schema(v) if isinstance(v, dict) else v
    if 'items' in schema and isinstance(schema['items'], dict):
        schema['items'] = _expand_schema(schema['items'])
    return schema


def _get_response_schema(path: str, method: str, status: str = '200') -> dict:
    p = SPEC['paths'][path][method]['responses'][status]
    content = p.get('content', {})
    if not content:
        # Return generic StandardResponse if unspecified
        return _resolve_ref('#/components/schemas/StandardResponse')
    app_json = content.get('application/json')
    if not app_json:
        return _resolve_ref('#/components/schemas/StandardResponse')
    schema = app_json.get('schema', {'$ref': '#/components/schemas/StandardResponse'})
    return _expand_schema(schema)


@pytest.fixture(scope='module')
def client():
    app.config.update(TESTING=True)
    with app.test_client() as c:
        yield c


@pytest.mark.parametrize('path,method', [
    ('/api/audio/status', 'get'),
])
def test_status_schema_conformance(client, path, method):
    schema = _get_response_schema(path, method)
    resp = client.get(path)
    data = resp.get_json()
    jsonschema.validate(instance=data, schema=schema)
    assert isinstance(data.get('features'), dict)


@pytest.mark.parametrize('path,method,payload', [
    ('/api/audio/align', 'post', {}),
    ('/api/audio/analyze', 'post', {}),
])
def test_alignment_like_endpoints_envelope(client, path, method, payload):
    if os.getenv('FAST_TESTS') == '1':
        pytest.skip('Skipping heavier endpoints in FAST_TESTS mode')
    schema = _get_response_schema(path, method)
    resp = client.post(path, json=payload)
    data = resp.get_json()
    # Even on failure, envelope must validate against StandardResponse subset
    standard_schema = _expand_schema({'$ref': '#/components/schemas/StandardResponse'})
    jsonschema.validate(instance=data, schema=standard_schema)


def test_export_status_schema(client):
    # Create fake export task directly for deterministic test
    app_state = app.config['app_state']
    task_id = 'test-task-123'
    app_state['export_tasks'][task_id] = {
        'status': 'completed',
        'progress': 100,
        'filename': 'demo.mp4',
        'path': 'uploads/demo.mp4',
        'error': None,
        'message': 'Done',
        'started_at': '2025-01-01T00:00:00'
    }
    schema = _get_response_schema('/api/export/status/{task_id}', 'get')
    resp = client.get(f'/api/export/status/{task_id}')
    data = resp.get_json()
    # At least must match StandardResponse
    base_schema = _expand_schema({'$ref': '#/components/schemas/StandardResponse'})
    jsonschema.validate(instance=data, schema=base_schema)
    assert 'task' in data
