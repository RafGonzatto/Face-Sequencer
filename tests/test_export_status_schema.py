"""Tests for export status structured schema."""
from __future__ import annotations
import yaml, jsonschema, pytest
from app import app

with open('openapi.yaml','r',encoding='utf-8') as f:
    SPEC = yaml.safe_load(f)


def _expand(schema: dict):
    if '$ref' in schema:
        ref_name = schema['$ref'].split('/')[-1]
        return _expand(SPEC['components']['schemas'][ref_name])
    if 'allOf' in schema:
        merged={'type':'object','properties':{},'required':[]}
        for part in schema['allOf']:
            ex=_expand(part)
            if ex.get('type')=='object':
                merged['properties'].update(ex.get('properties',{}))
                merged['required']+=ex.get('required',[])
        return merged
    return schema

@pytest.fixture(scope='module')
def client():
    app.config.update(TESTING=True)
    with app.test_client() as c:
        yield c


def test_export_status_success_schema(client):
    # Seed a fake task
    app_state = app.config['app_state']
    task_id = 'schema-task-1'
    app_state['export_tasks'][task_id] = {
        'status': 'running',
        'progress': 25,
        'filename': 'demo.mp4',
        'path': 'uploads/demo.mp4',
        'error': None,
        'message': 'Working'
    }
    resp = client.get(f'/api/export/status/{task_id}')
    data = resp.get_json()
    std = _expand({'$ref': '#/components/schemas/StandardResponse'})
    jsonschema.validate(instance=data, schema=std)
    assert 'task' in data and isinstance(data['task'], dict)
