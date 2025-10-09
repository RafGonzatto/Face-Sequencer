# lipanim_core_demo.py - Demo version without moviepy dependency
import os
import json
import string
import time
from PIL import Image
from concurrent.futures import ThreadPoolExecutor, as_completed
import math

LETTERS = list(string.ascii_uppercase)

def load_letter_map_from_dir(folder):
    """Load letter to image mappings from directory"""
    # New rules:
    # - Single-letter files like "A.png" map directly to that letter.
    # - Group files like "A-E-I.png" map to each listed single-letter token (A, E, I).
    # - Multi-letter tokens (e.g., "CH" or variants like "Aa") are NOT expanded per character here.
    #   They will be handled by higher-level logic (digraphs, vowel-initial variants) during sequence build.
    # - Special files "fallback.png" and "pause.png" are skipped here.
    m: dict[str, str] = {}
    if not (folder and os.path.isdir(folder)):
        return m

    # Track priority so that explicit single-letter files override group assignments
    priority: dict[str, int] = {}  # lower number = higher priority

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
        # Ignore special placeholders here; they are handled by the app layer
        if base_lower in ("fallback", "pause"):
            continue

        # Direct single-letter filename (highest priority)
        if len(base) == 1 and base.upper() in LETTERS:
            assign(base.upper(), path, p=0)
            continue

        # Group tokens separated by '-': map only single-letter tokens
        if "-" in base:
            tokens = [t.strip() for t in base.replace(" ", "").split("-") if t.strip()]
            for t in tokens:
                tu = t.upper()
                # Only map true single-letter tokens (A..Z)
                if len(tu) == 1 and tu in LETTERS:
                    # Group files have lower priority than direct single-letter files
                    assign(tu, path, p=5)
            continue

        # Any other multi-letter names (e.g., "Aa", "CH") are variants/digraphs -> not assigned here
        # They will be interpreted later during sequence building.

    return m

def valid_img(p):
    """Check if path is a valid image file"""
    return bool(p) and os.path.isfile(p)

def build_sequence(text, letter_map, dur_ms, gap_ms, fallback=None):
    """Build animation sequence from text"""
    seq = []
    # First, find a default fallback image if none provided
    default_fallback = fallback
    if not default_fallback or not valid_img(default_fallback):
        # Look for any usable image in images folder
        images_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'images')
        if os.path.exists(images_dir):
            for img_file in os.listdir(images_dir):
                if img_file.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                    potential_fallback = os.path.join(images_dir, img_file)
                    if os.path.exists(potential_fallback):
                        default_fallback = potential_fallback
                        print(f"Using automatic fallback image: {default_fallback}")
                        break
    
    for ch in text:
        if ch == " ":
            if gap_ms > 0:
                # Add pause frame with fallback image reference
                seq.append({
                    "char": " ", 
                    "img": default_fallback,  # Use default_fallback directly, even for pauses 
                    "fallback_img": default_fallback,  # Add fallback for export 
                    "ms": gap_ms,
                    "is_pause": True
                })
            continue
        
        key = ch.upper()
        # Check if the character exists in the mapping
        if key in letter_map and valid_img(letter_map[key]):
            # Character is mapped to a valid image
            seq.append({
                "char": ch, 
                "img": letter_map[key], 
                "fallback_img": default_fallback,  # Always include fallback reference
                "ms": dur_ms
            })
        elif default_fallback and valid_img(default_fallback):
            # Character not mapped, use fallback and mark as symbol frame
            print(f"Using fallback for unmapped character: '{ch}'")
            seq.append({
                "char": ch, 
                "img": default_fallback,  # Use fallback image directly
                "fallback_img": default_fallback,  # Also store in fallback_img for consistency
                "ms": dur_ms,
                "is_symbol_fallback": True  # Mark this as a symbol fallback frame
            })
        else:
            # No valid fallback, but still add an entry to maintain sequence length
            # This shouldn't ever happen with proper configuration
            print(f"WARNING: No valid image or fallback for character: '{ch}'")
            seq.append({
                "char": ch, 
                "img": None,
                "fallback_img": None, 
                "ms": dur_ms,
                "is_symbol_fallback": True
            })
    return seq

def export_json(seq, path):
    """Export sequence to JSON file"""
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"frames": seq}, f, ensure_ascii=False, indent=2)

def export_mp4(seq, path, fps, crf, preset, bg=(0, 0, 0, 0), progress_callback=None):
    """Export sequence to MP4 video using optimized high-performance exporter
    
    Args:
        seq: List of frame dictionaries
        path: Output file path
        fps: Frames per second
        crf: Video quality (0-51, lower is better)
        preset: Encoding preset (ultrafast, fast, medium, slow, etc.)
        bg: Background color (r,g,b,a)
        progress_callback: Optional callback function to report progress
    
    Returns:
        bool: Success or failure
    """
    
    # Try optimized export first
    try:
        from app.core.export.high_performance_export import export_mp4_optimized
        
        print("Using optimized high-performance exporter")
        print("Frames: {}, FPS: {}, CRF: {}, Preset: {}".format(len(seq), fps, crf, preset))
        
        return export_mp4_optimized(
            seq=seq,
            path=path,
            fps=fps,
            crf=crf,
            preset=preset,
            progress_callback=progress_callback
        )
        
    except ImportError as e:
        print("High-performance exporter not available: {}".format(e))
        print("Falling back to standard MoviePy export...")
        
        # Fallback to original implementation
        return _export_mp4_fallback(seq, path, fps, crf, preset, bg, progress_callback)
    
    except Exception as e:
        print("Optimized export failed: {}".format(e))
        print("Falling back to standard export...")
        
        # Fallback to original implementation  
        return _export_mp4_fallback(seq, path, fps, crf, preset, bg, progress_callback)

def _export_mp4_fallback(seq, path, fps, crf, preset, bg=(0, 0, 0, 0), progress_callback=None):
    """Fallback export using original MoviePy implementation"""
    try:
        import tempfile
        import os
        import subprocess
        from PIL import Image, ImageDraw, ImageFont
        
        print("Fallback export: {} frames to {}".format(len(seq), path))
        print("Settings: FPS={}, CRF={}, Preset={}".format(fps, crf, preset))
        
        # Create temporary directory for frames
        temp_dir = tempfile.mkdtemp()
        frame_files = []
        
        # Standard dimensions
        STANDARD_WIDTH = 640
        STANDARD_HEIGHT = 480
        
        if progress_callback:
            progress_callback(0, "Starting fallback export process")
        
        total_frames = len(seq)
        
        # Process frames sequentially  
        for i, frame in enumerate(seq):
            frame_filename = os.path.join(temp_dir, f"frame_{i:06d}.png")
            
            # Get image path
            img_path = frame.get('img') or frame.get('fallback_img')
            
            # Create or load image
            if not img_path or not os.path.exists(img_path):
                # Create simple fallback
                img = Image.new('RGBA', (STANDARD_WIDTH, STANDARD_HEIGHT), (0, 0, 0, 255))
                draw = ImageDraw.Draw(img)
                
                # Draw character
                char = frame.get('char', '?')
                try:
                    font = ImageFont.load_default()
                    bbox = draw.textbbox((0, 0), char, font=font)
                    text_width = bbox[2] - bbox[0] 
                    text_height = bbox[3] - bbox[1]
                    x = (STANDARD_WIDTH - text_width) // 2
                    y = (STANDARD_HEIGHT - text_height) // 2
                    draw.text((x, y), char, fill=(255, 255, 255, 255), font=font)
                except:
                    # Simple fallback without font
                    x = STANDARD_WIDTH // 2 - 20
                    y = STANDARD_HEIGHT // 2 - 20
                    draw.text((x, y), char, fill=(255, 255, 255, 255))
                
            else:
                # Load existing image
                try:
                    img = Image.open(img_path).convert('RGBA')
                    if img.size != (STANDARD_WIDTH, STANDARD_HEIGHT):
                        img = img.resize((STANDARD_WIDTH, STANDARD_HEIGHT), Image.Resampling.LANCZOS)
                except Exception as e:
                    print("Error loading {}: {}".format(img_path, e))
                    img = Image.new('RGBA', (STANDARD_WIDTH, STANDARD_HEIGHT), (255, 0, 0, 255))
            
            # Save frame
            img.save(frame_filename, 'PNG')
            frame_files.append(frame_filename)
            
            # Update progress
            if progress_callback and i % 50 == 0:
                progress = int((i / total_frames) * 80) + 10
                progress_callback(progress, f"Processing frames: {i+1}/{total_frames}")
        
        print("Generated {} frames".format(len(frame_files)))
        
        # Create FFmpeg input file list
        if progress_callback:
            progress_callback(85, "Preparing FFmpeg encoding")
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        
        # Create temporary file listing all frames with durations
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            image_list_path = f.name
            for i, frame_path in enumerate(frame_files):
                normalized_path = frame_path.replace('\\', '/')
                f.write(f"file '{normalized_path}'\n")
                if i < len(frame_files):
                    # Use frame duration from sequence
                    try:
                        fr_ms = max(1, int(seq[i].get('ms', 1000 // fps)))
                    except:
                        fr_ms = 1000 // fps
                    f.write(f"duration {fr_ms/1000.0}\n")
            # Duplicate last frame for FFmpeg concat
            if frame_files:
                normalized_path = frame_files[-1].replace('\\', '/')
                f.write(f"file '{normalized_path}'\n")
        
        # Build FFmpeg command
        ffmpeg_cmd = [
            'ffmpeg', '-y',
            '-f', 'concat', '-safe', '0',
            '-i', image_list_path,
            '-c:v', 'libx264',
            '-preset', preset,
            '-crf', str(crf),
            '-pix_fmt', 'yuv420p',
            '-an',
            path
        ]
        
        print("Running FFmpeg: {}".format(' '.join(ffmpeg_cmd)))
        
        # Run FFmpeg
        process = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
        
        # Clean up temp file
        try:
            os.unlink(image_list_path)
        except:
            pass
        
        if process.returncode != 0:
            error_msg = "FFmpeg failed: {}".format(process.stderr)
            print("ERROR: {}".format(error_msg))
            if progress_callback:
                progress_callback(-1, error_msg)
            return False
        
        # Clean up frame files
        if progress_callback:
            progress_callback(95, "Cleaning up temporary files")
        
        try:
            for frame_file in frame_files:
                if os.path.exists(frame_file):
                    os.remove(frame_file)
            os.rmdir(temp_dir)
        except Exception as cleanup_error:
            print("Cleanup warning: {}".format(cleanup_error))
        
        if progress_callback:
            progress_callback(100, "Video export complete")
        
        print("Successfully created video: {}".format(path))
        return True
        
    except Exception as e:
        print("Fallback export error: {}".format(e))
        if progress_callback:
            progress_callback(-1, "Error: {}".format(e))
        return False