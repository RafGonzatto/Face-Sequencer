"""Tests for folder scan and thumbnail mapping endpoints.

Covers:
 - /api/folder/scan happy path + invalid input
 - Path normalization (absolute)
 - Mapping payload structure (mapped, path = basename, abs_path present)
 - /api/mapping/thumbnails generation and base64 format
"""
from __future__ import annotations

import base64
import os
from pathlib import Path
import tempfile
from PIL import Image
import pytest
from app import app


@pytest.fixture(scope="module")
def client():
    app.config.update(TESTING=True)
    with app.test_client() as c:
        yield c


def _create_images(dir_path: str, mapping: dict[str, tuple[int,int,int]]):
    """Helper: create simple solid-color PNG images.

    mapping: {"A": (r,g,b)} will produce A.png with given color.
    """
    for letter, color in mapping.items():
        img_path = os.path.join(dir_path, f"{letter}.png")
        Image.new("RGBA", (64, 64), (*color, 255)).save(img_path)


def test_folder_scan_basic_structure(client):
    with tempfile.TemporaryDirectory() as tmp:
        _create_images(tmp, {"A": (255,0,0), "B": (0,255,0)})
        resp = client.post('/api/folder/scan', json={'path': tmp})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        mappings = data['mappings']
        # A and B mapped, Z should exist but unmapped
        assert mappings['A']['mapped'] is True
        assert mappings['A']['path'] == 'A.png'  # basename only
        assert 'abs_path' in mappings['A'] and os.path.isabs(mappings['A']['abs_path'])
        assert mappings['B']['mapped'] is True
        assert mappings['B']['path'] == 'B.png'
        assert mappings['Z']['mapped'] is False


def test_folder_scan_invalid_path(client):
    resp = client.post('/api/folder/scan', json={'path': 'nonexistent_dir_12345'})
    assert resp.status_code == 400
    data = resp.get_json()
    assert data['success'] is False
    assert data['error_type'] == 'invalid_input'


def test_thumbnails_generation(client):
    with tempfile.TemporaryDirectory() as tmp:
        _create_images(tmp, {"A": (10,10,200), "C": (200,10,10), "X": (10,200,10)})
        # Scan first (stores mapping & folder_path in app state)
        scan_resp = client.post('/api/folder/scan', json={'path': tmp})
        assert scan_resp.status_code == 200
        letters = ['A','C','X']
        thumb_resp = client.post('/api/mapping/thumbnails', json={'letters': letters, 'size': 48})
        assert thumb_resp.status_code == 200
        tdata = thumb_resp.get_json()
        assert tdata['success'] is True
        assert tdata['generated'] == len(letters)
        thumbs = tdata['thumbnails']
        assert set(thumbs.keys()) == set(letters)
        # Validate base64 header
        for letter, b64url in thumbs.items():
            assert b64url.startswith('data:image/png;base64,')
            raw = b64url.split(',',1)[1]
            # base64 decoding should not raise
            base64.b64decode(raw)


def test_thumbnails_ignore_unmapped_letter(client):
    with tempfile.TemporaryDirectory() as tmp:
        _create_images(tmp, {"M": (100,100,100)})
        client.post('/api/folder/scan', json={'path': tmp})
        # Request thumbnails for mapped + unmapped
        resp = client.post('/api/mapping/thumbnails', json={'letters': ['M','Z']})
        assert resp.status_code == 200
        data = resp.get_json()
        # Only M generated
        assert data['generated'] == 1
        assert list(data['thumbnails'].keys()) == ['M']
