"""WP005: Ensure generated openapi_schemas.json is in sync with build output.

This guards against manual edits to the generated JSON bundle and detects
forgotten regeneration when modular fragments change.
"""
from __future__ import annotations

import json
import subprocess
import hashlib
from pathlib import Path
import pytest

ROOT = Path(__file__).parent.parent


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


@pytest.mark.order(-1)
def test_generated_schema_is_current(tmp_path: Path, monkeypatch):
    """Rebuild into temp dir and compare hash to committed file."""
    committed = ROOT / 'openapi_schemas.json'
    assert committed.exists(), 'Committed openapi_schemas.json missing'

    # Run build script in temp directory to avoid overwriting committed artifacts
    build_script = ROOT / 'build_openapi.py'
    result = subprocess.run(
        ["python", str(build_script), "--json-schema"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )
    rebuilt = tmp_path / 'openapi_schemas.json'
    assert rebuilt.exists(), 'Rebuilt schema file missing'

    if _sha256(committed) != _sha256(rebuilt):
        # Provide diff context (sizes + first 200 chars) to help debugging
        committed_text = committed.read_text(encoding='utf-8')
        rebuilt_text = rebuilt.read_text(encoding='utf-8')
        msg = (
            'openapi_schemas.json drift detected. Regenerate with:\n'
            '  python build_openapi.py --json-schema\n'
            f'Committed hash: {_sha256(committed)} New hash: {_sha256(rebuilt)}\n'
            f'Committed head: {committed_text[:200]!r}\n'
            f'Rebuilt head: {rebuilt_text[:200]!r}'
        )
        pytest.fail(msg)
