"""lipanim_core.py - Core functionality extracted from original Tkinter app.

Compatibility Note:
 Some Phase 4 tests import `LipAnimCore` class from this module. Earlier refactors
 left only functional helpers (load_letter_map_from_dir, build_sequence, etc.).
 To maintain backward compatibility for tests without reintroducing heavy state,
 we provide a very light wrapper class exposing the expected API surface used by tests.
"""
import os
import json
import string
from PIL import Image
from moviepy.editor import ImageClip, concatenate_videoclips


class LipAnimCore:  # Minimal shim for legacy tests
    """Lightweight facade preserving old class-based interface.

    Methods delegate to the module-level functions implemented after refactor.
    Only the subset required by tests is implemented; extend if new attributes
    are accessed. Avoid expensive initialization to keep tests fast.
    """

    def __init__(self, frame_duration_ms: int = 120, gap_duration_ms: int = 80):
        self.frame_duration_ms = frame_duration_ms
        self.gap_duration_ms = gap_duration_ms
        self.letter_map: dict[str, str] = {}
        self.fallback_image: str | None = None

    # Loading / mapping -------------------------------------------------
    def load_mapping(self, folder: str):
        self.letter_map = load_letter_map_from_dir(folder)
        return self.letter_map

    # Sequence building -------------------------------------------------
    def build_sequence(self, text: str) -> list[dict]:
        return build_sequence(
            text,
            self.letter_map,
            self.frame_duration_ms,
            self.gap_duration_ms,
            fallback=self.fallback_image,
        )

    # Export helpers ----------------------------------------------------
    def export_json(self, seq: list[dict], path: str):  # pragma: no cover - thin delegate
        export_json(seq, path)

    def export_mp4(
        self,
        seq: list[dict],
        path: str,
        fps: int = 30,
        crf: int = 18,
        preset: str = "medium",
    ):  # pragma: no cover - thin delegate
        export_mp4(seq, path, fps=fps, crf=crf, preset=preset)

    # Convenience for tests ---------------------------------------------
    def build_and_export_json(self, text: str, path: str):
        seq = self.build_sequence(text)
        self.export_json(seq, path)
        return seq


LETTERS = list(string.ascii_uppercase)

def load_letter_map_from_dir(folder):
    """Load letter to image mappings from directory"""
    # See lipanim_core_demo.load_letter_map_from_dir for rules
    m: dict[str, str] = {}
    if not (folder and os.path.isdir(folder)):
        return m

    priority: dict[str, int] = {}

    def assign(letter: str, path: str, p: int):
        if letter not in LETTERS:
            return
        prev_p = priority.get(letter, 10_000)
        if p <= prev_p:
            m[letter] = path
            priority[letter] = p

    for fn in os.listdir(folder):
        path = os.path.join(folder, fn)
        name, ext = os.path.splitext(fn)
        if ext.lower() not in (".png", ".jpg", ".jpeg", ".webp", ".bmp"):
            continue
        base = name.strip()
        base_lower = base.lower()
        if base_lower in ("fallback", "pause"):
            continue
        if len(base) == 1 and base.upper() in LETTERS:
            assign(base.upper(), path, p=0)
            continue
        if "-" in base:
            tokens = [t.strip() for t in base.replace(" ", "").split("-") if t.strip()]
            for t in tokens:
                tu = t.upper()
                if len(tu) == 1 and tu in LETTERS:
                    assign(tu, path, p=5)
            continue
        # multi-letter tokens are ignored at scan time
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