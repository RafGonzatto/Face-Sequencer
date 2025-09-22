# lipanim_core.py - Core functionality extracted from original Tkinter app
import os
import json
import string
from PIL import Image
from moviepy.editor import ImageClip, concatenate_videoclips

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
    """Export sequence to MP4 video"""
    imgs = [s for s in seq if s["img"]]
    if not imgs:
        raise RuntimeError("Empty sequence.")
    
    from PIL import Image as PILImage
    w, h = PILImage.open(imgs[0]["img"]).size
    clips = []
    tmp_blanks = []
    
    for f in seq:
        if f["img"] is None:
            # Create blank frame for pauses
            im = PILImage.new("RGBA", (w, h), bg)
            tmp = os.path.join(os.path.dirname(path) or ".", f"__blank_{f['ms']}.png")
            im.save(tmp)
            tmp_blanks.append(tmp)
            clips.append(ImageClip(tmp).set_duration(max(f["ms"], 1) / 1000.0))
        else:
            c = ImageClip(f["img"]).set_duration(max(f["ms"], 1) / 1000.0)
            if c.w != w or c.h != h:
                c = c.resize(newsize=(w, h))
            clips.append(c)
    
    video = concatenate_videoclips(clips, method="compose").set_fps(fps)
    video.write_videofile(
        path, 
        codec="libx264", 
        audio=False, 
        fps=fps, 
        preset=preset, 
        ffmpeg_params=["-crf", str(crf), "-pix_fmt", "yuv420p"]
    )
    video.close()
    
    # Clean up temporary files
    for p in tmp_blanks:
        try:
            os.remove(p)
        except:
            pass