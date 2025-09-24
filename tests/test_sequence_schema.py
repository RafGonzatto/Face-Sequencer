"""Schema-oriented tests for sequence endpoints.

Validates that sequence update/reorder/delete endpoints accept the documented
request payload shapes and respond with the standardized envelope. Also checks
frame retrieval shape.
"""
from __future__ import annotations

import yaml
import jsonschema
import pytest
from app import app
import io
import numpy as np
from pathlib import Path

with open('openapi.yaml', 'r', encoding='utf-8') as f:
    SPEC = yaml.safe_load(f)


def _schema(name: str) -> dict:
    return SPEC['components']['schemas'][name]


def _expand(schema: dict) -> dict:
    if '$ref' in schema:
        ref_name = schema['$ref'].split('/')[-1]
        return _expand(SPEC['components']['schemas'][ref_name])
    if 'allOf' in schema:
        merged: dict = {'type': 'object', 'properties': {}, 'required': []}
        for part in schema['allOf']:
            exp = _expand(part)
            merged['properties'].update(exp.get('properties', {}))
            if 'required' in exp:
                merged['required'].extend(exp['required'])
        return merged
    if schema.get('type') == 'object':
        for k, v in list(schema.get('properties', {}).items()):
            if isinstance(v, dict):
                schema['properties'][k] = _expand(v)
    return schema


@pytest.fixture(scope='module')
def client():
    app.config.update(TESTING=True)
    with app.test_client() as c:
        yield c


@pytest.fixture(scope='module')
def seed_audio_file():
    """Create a tiny silent wav file to satisfy audio existence checks if needed."""
    import wave
    audio_dir = Path('uploads')
    audio_dir.mkdir(exist_ok=True)
    filename = 'test_silence.wav'
    path = audio_dir / filename
    if not path.exists():
        with wave.open(str(path), 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(b'\x00' * 16000)  # 1 second silence
    return filename


def test_update_request_schema_present():
    assert 'SequenceUpdateRequest' in SPEC['components']['schemas']


def test_sequence_update_endpoint(client):
    # Build a minimal valid request (frame 0 may not exist yet, expect graceful error envelope)
    payload = {"frame_id": 0, "updates": {"duration": 120}}
    resp = client.post('/api/sequence/update', json=payload)
    data = resp.get_json()
    std = _expand({'$ref': '#/components/schemas/StandardResponse'})
    jsonschema.validate(instance=data, schema=std)
    assert 'success' in data


def test_sequence_reorder_endpoint(client):
    payload = {"from_index": 0, "to_index": 0}
    resp = client.post('/api/sequence/reorder', json=payload)
    data = resp.get_json()
    std = _expand({'$ref': '#/components/schemas/StandardResponse'})
    jsonschema.validate(instance=data, schema=std)


def test_sequence_delete_endpoint(client):
    payload = {"frame_id": 0}
    resp = client.post('/api/sequence/delete', json=payload)
    data = resp.get_json()
    std = _expand({'$ref': '#/components/schemas/StandardResponse'})
    jsonschema.validate(instance=data, schema=std)


def test_sequence_frame_get_shape(client):
    resp = client.get('/api/sequence/frame/0')
    data = resp.get_json()
    std = _expand({'$ref': '#/components/schemas/StandardResponse'})
    jsonschema.validate(instance=data, schema=std)
    # Frame-specific optional fields (not all ensured present)
    assert 'success' in data


def test_sequence_build_from_audio_schema(client, seed_audio_file):
    spec_req = _schema('SequenceBuildFromAudioRequest')
    # Simple synthetic alignment token list
    tokens = [
        {"type": "word", "text": "Hi", "start_ms": 0, "end_ms": 200},
        {"type": "gap", "start_ms": 200, "end_ms": 300},
        {"type": "word", "text": "A", "start_ms": 300, "end_ms": 500}
    ]
    payload = {
        "audio_filename": seed_audio_file,
        "text": "Hi A",
        "alignment_tokens": tokens
    }
    # Validate request shape against schema
    jsonschema.validate(instance=payload, schema=spec_req)
    resp = client.post('/api/sequence/build-from-audio', json=payload)
    data = resp.get_json()
    std = _expand({'$ref': '#/components/schemas/StandardResponse'})
    jsonschema.validate(instance=data, schema=std)
    # On success we expect sequence present; on failure still envelope valid
    if data.get('success'):
        assert isinstance(data.get('sequence'), list)
        assert data.get('stats', {}).get('total_frames') == len(data.get('sequence'))
