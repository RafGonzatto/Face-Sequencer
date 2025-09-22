# lipanim_core_demo.py - Demo version without moviepy dependency
import os
import json
import string
from PIL import Image

LETTERS = list(string.ascii_uppercase)

def load_letter_map_from_dir(folder):
    """Load letter to image mappings from directory"""
    m = {}
    if folder and os.path.isdir(folder):
        for fn in os.listdir(folder):
            path = os.path.join(folder, fn)
            name, ext = os.path.splitext(fn)
            if ext.lower() not in (".png", ".jpg", ".jpeg", ".webp", ".bmp"):
                continue
            for ch in name.upper():
                if ch in LETTERS:
                    m[ch] = path
    return m

def valid_img(p):
    """Check if path is a valid image file"""
    return bool(p) and os.path.isfile(p)

def build_sequence(text, letter_map, dur_ms, gap_ms, fallback=None):
    """Build animation sequence from text"""
    seq = []
    for ch in text:
        if ch == " ":
            if gap_ms > 0:
                seq.append({"char": " ", "img": None, "ms": gap_ms})
            continue
        key = ch.upper()
        img = letter_map.get(key) or (fallback if valid_img(fallback) else None)
        if img:
            seq.append({"char": ch, "img": img, "ms": dur_ms})
    return seq

def export_json(seq, path):
    """Export sequence to JSON file"""
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"frames": seq}, f, ensure_ascii=False, indent=2)

def export_mp4(seq, path, fps, crf, preset, bg=(0, 0, 0, 0)):
    """Export sequence to MP4 video (demo version - simulated)"""
    # This is a demo function that simulates video export
    # In the full version, this would use MoviePy
    
    print(f"Demo: Would export {len(seq)} frames to {path}")
    print(f"Settings: FPS={fps}, CRF={crf}, Preset={preset}")
    
    # Create a placeholder file to simulate export
    with open(path, 'w') as f:
        f.write("Demo video export - install MoviePy for actual video generation")
    
    return True