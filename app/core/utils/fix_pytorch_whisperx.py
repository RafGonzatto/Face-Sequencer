"""Deprecated: fix_pytorch_whisperx

WP002 introduced a centralized compatibility layer in `pytorch_compat.py`.
This script is retained as a shim for older automation referencing it, but
it no longer performs global monkey patches. Prefer importing:

    from pytorch_compat import safe_load, patched_load_context

and use those APIs directly.
"""
from __future__ import annotations
import sys
from pytorch_compat import (
    is_problematic_version,
    ensure_whisperx_safe_globals,
    patched_load_context,
)

def patch_all():  # Backwards compatibility no-op
    if is_problematic_version():
        ensure_whisperx_safe_globals()
    return True

if __name__ == "__main__":  # Minimal verification
    patched = patch_all()
    print(f"pytorch_compat active (problematic_version={is_problematic_version()}, patched={patched})")
    sys.exit(0)