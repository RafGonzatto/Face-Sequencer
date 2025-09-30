"""Shared export utilities: color conversion, payload/video hashing, text wrapping, timestamp formatting.

Consolidated from legacy export subtitle burn-in logic so routes can import
helpers instead of duplicating ad-hoc inline functions.
"""
from __future__ import annotations
import hashlib, json, re
from typing import Iterable, Dict, Any

__all__ = [
    'hex_to_ass_color',
    'hash_video_file',
    'hash_payload',
    'combined_export_hash',
    'wrap_text_balanced',
    'format_ass_timestamp'
]

def hex_to_ass_color(hex_color: str | None, alpha_percent: float | int | None = None) -> str:
    """Convert #RRGGBB or #RGB plus optional alpha percent -> ASS &HAABBGGRR."""
    try:
        if not hex_color:
            hex_color = '#FFFFFF'
        hc = hex_color.strip().lstrip('#')
        if len(hc) == 3:
            hc = ''.join(c * 2 for c in hc)
        if len(hc) != 6:
            return '&H00FFFFFF'
        r = int(hc[0:2], 16); g = int(hc[2:4], 16); b = int(hc[4:6], 16)
        if alpha_percent is None:
            alpha = 0
        else:
            try:
                alpha_f = max(0.0, min(100.0, float(alpha_percent))) / 100.0
                alpha = int(alpha_f * 255)
            except Exception:
                alpha = 0
        return f"&H{alpha:02X}{b:02X}{g:02X}{r:02X}"
    except Exception:
        return '&H00FFFFFF'

def hash_video_file(path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    try:
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(chunk_size), b''):
                h.update(chunk)
    except Exception:
        return ''
    return h.hexdigest()

def hash_payload(payload: Dict[str, Any]) -> str:
    try:
        return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()
    except Exception:
        return ''

def combined_export_hash(video_hash: str, payload_hash: str) -> str:
    return hashlib.sha256(f"{video_hash}:{payload_hash}".encode('utf-8')).hexdigest()

def wrap_text_balanced(text: str, target_line_chars: int) -> str:
    if not text:
        return ''
    raw = re.sub(r'<br\s*/?>', '\n', text.replace('\r\n', '\n'), flags=re.IGNORECASE)
    if '\n' in raw:
        parts = [p.strip() for p in raw.split('\n') if p.strip()]
    else:
        words = raw.split()
        parts: list[str] = []
        line: list[str] = []
        count = 0
        for w in words:
            wlen = len(w)
            if count + wlen + (1 if line else 0) > target_line_chars and line:
                parts.append(' '.join(line)); line = [w]; count = wlen
            else:
                line.append(w); count += wlen + (1 if line[:-1] else 0)
        if line:
            parts.append(' '.join(line))
    return '\n'.join(parts)

def format_ass_timestamp(ms: int | float | None) -> str:
    if ms is None:
        ms = 0
    ms = max(0, int(ms))
    h = ms // 3600000; ms -= h * 3600000
    m = ms // 60000; ms -= m * 60000
    s = ms // 1000; cs = int((ms - s * 1000)/10)
    return f"{h:d}:{m:02d}:{s:02d}.{cs:02d}"
