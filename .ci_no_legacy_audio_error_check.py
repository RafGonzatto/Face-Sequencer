"""Simple CI check script to fail if new usages of legacy AudioProcessingError appear outside the shim.
Run this in CI (e.g. via `python .ci_no_legacy_audio_error_check.py`).
"""
from __future__ import annotations
import pathlib
import sys
import re

ROOT = pathlib.Path(__file__).parent
TARGET = 'AudioProcessingError'
ALLOW_FILES = {
    'audio_error_handling.py',  # deprecated shim retained
    'audio_exceptions.py',      # mapping import guard
    '.ci_no_legacy_audio_error_check.py',  # self
    'audio_error_adapter.py',   # mentions term only in docstring examples
}
pattern = re.compile(r'\bAudioProcessingError\b')
violations = []
for path in ROOT.rglob('*.py'):
    if path.name in ALLOW_FILES:
        continue
    text = path.read_text(encoding='utf-8', errors='ignore')
    if pattern.search(text):
        violations.append(path)

if violations:
    print('❌ Legacy AudioProcessingError usage detected in:')
    for v in violations:
        print(f'  - {v.relative_to(ROOT)}')
    print('\nPlease migrate to AlignmentError.')
    sys.exit(1)
else:
    print('✅ No disallowed AudioProcessingError usages found.')
