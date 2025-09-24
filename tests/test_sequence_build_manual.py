"""Tests for manual sequence build endpoint /api/sequence/build.
Covers edge cases: empty text, unmapped characters, fallback logic, mixed mapped/unmapped.
"""
from __future__ import annotations
import os
import io
from pathlib import Path
from PIL import Image
import pytest
from app import app, app_state

@pytest.fixture()
def client():
    app.config.update(TESTING=True)
    with app.test_client() as c:
        # Reset project state per test
        state = app_state['current_project']
        state['text'] = ''
        state['sequence'] = []
        state['letter_map'] = {}
        state['fallback_image'] = ''
        yield c


def _make_image(path: Path, color=(128, 128, 128)):
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new('RGB', (64, 64), color)
    img.save(str(path), 'PNG')


def test_build_empty_text(client):
    # Ensure empty text returns success with empty sequence
    resp = client.post('/api/sequence/build')
    data = resp.get_json()
    assert resp.status_code == 200
    assert data['success'] is True
    assert data['sequence'] == []
    assert data['stats']['total_frames'] == 0


def test_build_with_unmapped_chars_and_no_fallback(client, tmp_path):
    # Provide text but no letter_map and no fallback -> frames with fallback markers but img None allowed
    app_state['current_project']['text'] = 'ABC'
    resp = client.post('/api/sequence/build')
    data = resp.get_json()
    assert resp.status_code == 200
    seq = data['sequence']
    assert len(seq) == 3
    # Each frame should have char upper and ms
    for frame in seq:
        assert frame['char'] in 'ABC'
        assert 'ms' in frame
        # fallback_img only appears if we had explicit fallback; here we expect absence
        assert 'fallback_img' not in frame


def test_build_with_fallback_for_unmapped(client, tmp_path):
    # Create a fallback image
    fallback = tmp_path / 'fallback.png'
    _make_image(fallback, (200, 10, 10))
    state = app_state['current_project']
    state['fallback_image'] = str(fallback)
    state['text'] = 'ABZ'  # Z is unmapped; A/B mapped next

    # Create letter_map entries for A and B only
    a_img = tmp_path / 'A.png'; _make_image(a_img, (0, 255, 0))
    b_img = tmp_path / 'B.png'; _make_image(b_img, (0, 0, 255))
    state['letter_map'] = {
        'A': {'abs_path': str(a_img), 'path': 'A.png', 'mapped': True},
        'B': {'abs_path': str(b_img), 'path': 'B.png', 'mapped': True},
    }

    resp = client.post('/api/sequence/build')
    data = resp.get_json(); seq = data['sequence']
    assert len(seq) == 3
    # A and B should use their images; Z should fallback
    a_frame, b_frame, z_frame = seq
    assert a_frame['img'].endswith('A.png')
    assert b_frame['img'].endswith('B.png')
    assert z_frame['img'] == str(fallback)
    assert z_frame.get('is_symbol_fallback') is True


def test_build_with_spaces_and_pause_duration(client, tmp_path):
    # Setup mapping for A only, include space handling
    state = app_state['current_project']
    state['text'] = 'A A'
    a_img = tmp_path / 'A.png'; _make_image(a_img, (10, 150, 10))
    state['letter_map'] = {'A': {'abs_path': str(a_img), 'path': 'A.png', 'mapped': True}}
    # Override settings
    state['settings']['frame_duration'] = 90
    state['settings']['pause_duration'] = 140

    resp = client.post('/api/sequence/build')
    data = resp.get_json(); seq = data['sequence']
    assert len(seq) == 3  # A, space, A
    assert seq[0]['ms'] == 90
    assert seq[1]['is_pause'] is True and seq[1]['ms'] == 140
    assert seq[2]['ms'] == 90


def test_build_updates_project_state(client):
    state = app_state['current_project']
    state['text'] = 'AB'
    resp = client.post('/api/sequence/build')
    assert resp.status_code == 200
    assert len(app_state['current_project']['sequence']) == 2
    assert app_state['current_project']['timing_mode'] == 'manual'
