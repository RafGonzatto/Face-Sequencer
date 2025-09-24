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
    """Export sequence to MP4 video using MoviePy
    
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
    try:
        from moviepy.editor import ImageSequenceClip
        import numpy as np
        import tempfile
        import os
        import time
        from PIL import Image, ImageDraw
        
        # Import our compatibility layer
        try:
            from moviepy_compat import get_compatible_write_params
            has_compat = True
            print("Using MoviePy compatibility helpers")
        except ImportError:
            has_compat = False
            print("MoviePy compatibility helpers not available")
        
        print(f"Exporting {len(seq)} frames to {path}")
        print(f"Settings: FPS={fps}, CRF={crf}, Preset={preset}")
        
        # Create temporary directory for frames
        temp_dir = tempfile.mkdtemp()
        frame_files = []
        
        # Define standard dimensions for all frames
        # Default to 640x480 if not specified elsewhere
        STANDARD_WIDTH = 640
        STANDARD_HEIGHT = 480
        
        # Report initial progress
        if progress_callback:
            progress_callback(0, "Starting export process")
        
        # Generate frames from sequence
        total_frames = len(seq)
        
        # First scan to determine optimal dimensions
        if progress_callback:
            progress_callback(2, f"Scanning {total_frames} images for dimensions")
        
        # Initialize with default dimensions
        max_width = STANDARD_WIDTH
        max_height = STANDARD_HEIGHT
        
        # First pass - determine the largest dimensions needed
        for i, frame in enumerate(seq):
            if not frame.get('is_pause', False):
                img_path = frame.get('img')
                if img_path and os.path.exists(img_path):
                    try:
                        with Image.open(img_path) as img:
                            width, height = img.size
                            max_width = max(max_width, width)
                            max_height = max(max_height, height)
                    except Exception as e:
                        print(f"Error checking dimensions for {img_path}: {e}")
        
        print(f"Using standard dimensions: {max_width}x{max_height}")
        
        # ---------------- Parallel frame generation (WP004) ----------------
        def _prepare_single(i_frame):
            i, frame = i_frame
            try:
                img_path = frame.get('img')
                fallback_needed = False
                if frame.get('is_pause', False) and not img_path:
                    fallback_needed = True
                if frame.get('is_symbol_fallback', False):
                    fallback_needed = True
                if not img_path or not os.path.exists(img_path):
                    fallback_needed = True
                if fallback_needed:
                    fallback_img_path = frame.get('fallback_img')
                    if fallback_img_path and os.path.exists(fallback_img_path):
                        img_path = fallback_img_path
                if not img_path or not os.path.exists(img_path):
                    default_fallback = None
                    potential_folders = [
                        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'images'),
                        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'debug_export'),
                        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'outros')
                    ]
                    for folder in potential_folders:
                        if os.path.exists(folder):
                            image_files = [f for f in os.listdir(folder) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp'))]
                            if image_files:
                                default_fallback = os.path.join(folder, image_files[0])
                                break
                    if default_fallback and os.path.exists(default_fallback):
                        img_path = default_fallback
                if img_path and os.path.exists(img_path):
                    try:
                        pil_img = Image.open(img_path).convert('RGBA')
                        current_width, current_height = pil_img.size
                        if current_width != max_width or current_height != max_height:
                            new_img = Image.new('RGBA', (max_width, max_height), (0, 0, 0, 0))
                            paste_x = (max_width - current_width) // 2
                            paste_y = (max_height - current_height) // 2
                            new_img.paste(pil_img, (paste_x, paste_y), pil_img)
                            pil_img = new_img
                        img = np.array(pil_img)
                    except Exception as e:
                        img = np.zeros((max_height, max_width, 4), dtype=np.uint8)
                else:
                    img = np.zeros((max_height, max_width, 4), dtype=np.uint8)
                    img[:, :, 0] = 255
                    img[:, :, 2] = 255
                frame_duration = frame.get('ms', 100) / 1000.0
                if frame_duration <= 0:
                    frame_duration = 0.1
                frame_count = max(1, int(round(frame_duration * fps)))
                return i, img, frame_count
            except Exception as e:
                blank = np.zeros((max_height, max_width, 4), dtype=np.uint8)
                return i, blank, 1

        max_workers = min(8, os.cpu_count() or 4)
        results = [None] * total_frames
        last_update_time = time.time()
        update_interval = 0.1  # Update progress more frequently (100ms) for smoother UI
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(_prepare_single, item): item[0] for item in enumerate(seq)}
            for idx, fut in enumerate(as_completed(futures)):
                i, img, frame_count = fut.result()
                frame_path = os.path.join(temp_dir, f"frame_{i:05d}.png")
                Image.fromarray(img).save(frame_path)
                frame_files.append(frame_path)
                if frame_count > 1:
                    frame_files.extend([frame_path] * (frame_count - 1))
                
                # More frequent progress updates with more detailed information
                current_time = time.time()
                if progress_callback and (idx % max(1, total_frames // 40) == 0 or 
                                        current_time - last_update_time >= update_interval):
                    last_update_time = current_time
                    progress_percent = int(5 + (idx / total_frames) * 35)  # Scale from 5% to 40%
                    percent_complete = int((idx / total_frames) * 100)
                    progress_callback(
                        progress_percent, 
                        f"Preparing frames: {percent_complete}% complete ({idx+1}/{total_frames})"
                    )
        
        # Report progress with more detail
        if progress_callback:
            progress_callback(40, f"Creating video clip from {len(frame_files)} frames")
        
        # Verify all frames have the same dimensions before creating the clip
        if progress_callback:
            progress_callback(42, "Verifying frame consistency and preparing for encoding")
        
        # Final check - verify all PNGs have identical dimensions
        from PIL import Image
        frame_dimensions = []
        for frame_file in frame_files[:5]:  # Check just a few files for efficiency
            if os.path.exists(frame_file):
                with Image.open(frame_file) as img:
                    frame_dimensions.append(img.size)
        
        # Check if all dimensions are the same
        if len(set(frame_dimensions)) > 1:
            error_msg = f"Frame dimension mismatch detected: {set(frame_dimensions)}"
            print(f"ERROR: {error_msg}")
            if progress_callback:
                progress_callback(-1, error_msg)
            return False
            
        # Using direct FFmpeg approach instead of MoviePy for more reliability
        try:
            # Add more debug information about the frames before creating the clip
            print(f"Creating clip from {len(frame_files)} frames at {fps} fps")
            if len(frame_files) > 0:
                print(f"First frame: {frame_files[0]}")
                
                # Check a sample of frames to ensure they exist
                for i in range(min(5, len(frame_files))):
                    frame_index = i * (len(frame_files) // 5) if len(frame_files) > 5 else i
                    if frame_index < len(frame_files):
                        frame_path = frame_files[frame_index]
                        if os.path.exists(frame_path):
                            frame_size = os.path.getsize(frame_path)
                            print(f"Frame {frame_index}: {frame_path} (size: {frame_size} bytes)")
                        else:
                            print(f"Frame {frame_index}: {frame_path} does not exist!")
            
            # Report progress with more detailed information
            if progress_callback:
                total_frames = len(frame_files)
                estimated_duration = total_frames / fps
                progress_callback(
                    48, 
                    f"Starting video encoding with FFmpeg: {total_frames} frames at {fps} FPS (~{estimated_duration:.1f}s)"
                )
            
            # Ensure the directory exists
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            
            # Use direct FFmpeg approach instead of relying on MoviePy
            # Create a temporary file listing all frames
            import tempfile
            import subprocess
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                image_list_path = f.name
                # Use a fixed duration for each frame based on FPS
                frame_duration = 1.0 / fps
                
                for frame_path in frame_files:
                    # Normalize Windows paths for FFmpeg
                    normalized_path = frame_path.replace('\\', '/')
                    # Write the frame and its duration
                    f.write(f"file '{normalized_path}'\n")
                    f.write(f"duration {frame_duration}\n")
                
                # The last frame doesn't need a duration
                if frame_files:
                    normalized_path = frame_files[-1].replace('\\', '/')
                    f.write(f"file '{normalized_path}'\n")
            
            # Build FFmpeg command
            ffmpeg_cmd = [
                'ffmpeg',
                '-y',  # Overwrite output file
                '-f', 'concat',  # Use concat demuxer
                '-safe', '0',  # Don't check for absolute paths
                '-i', image_list_path,  # Input file list
                '-c:v', 'libx264',  # Use H.264 codec
                '-preset', preset,  # Encoding speed/compression tradeoff
                '-crf', str(crf),  # Quality level
                '-pix_fmt', 'yuv420p',  # Standard pixel format for compatibility
                '-an',  # No audio
                path  # Output path
            ]
            
            print("Running FFmpeg command:", ' '.join(ffmpeg_cmd))
            
            # Use subprocess to run FFmpeg with progress monitoring
            process = subprocess.Popen(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1
            )
            
            # Monitor FFmpeg progress with more frequent updates
            last_progress = 0
            last_update_time = time.time()
            update_interval = 0.2  # Update progress at most every 0.2 seconds for smoother UI
            while True:
                output_line = process.stderr.readline()
                if output_line == '' and process.poll() is not None:
                    break
                
                current_time = time.time()
                elapsed_since_update = current_time - last_update_time
                
                if output_line:
                    # Try to parse progress from FFmpeg output
                    if 'time=' in output_line:
                        try:
                            # Extract time information (e.g., time=00:00:12.34)
                            time_str = output_line.split('time=')[1].split(' ')[0]
                            # Parse the time in the format HH:MM:SS.MS
                            h, m, s = time_str.split(':')
                            seconds = float(h) * 3600 + float(m) * 60 + float(s)
                            
                            # Calculate progress as a percentage (estimate using total frame count)
                            total_duration = len(frame_files) / fps
                            progress_percent = min(95, 50 + int((seconds / total_duration) * 45))
                            
                            # Only update if progress has changed and enough time has passed
                            if (progress_percent > last_progress or elapsed_since_update >= update_interval) and progress_callback:
                                last_progress = progress_percent
                                last_update_time = current_time
                                
                                # Calculate more detailed percentage
                                encoding_percent = int((seconds / total_duration) * 100)
                                
                                # Send more detailed progress update
                                progress_callback(
                                    progress_percent, 
                                    f"Encoding video: {encoding_percent}% complete (frame {int(seconds * fps)}/{len(frame_files)})"
                                )
                        except Exception as e:
                            # If we can't parse progress, still show that we're working
                            if progress_callback and (elapsed_since_update >= update_interval):
                                last_update_time = current_time
                                if last_progress < 75:
                                    last_progress = 75
                                progress_callback(last_progress, f"Encoding video (progress at {last_progress}%)")
            
            # Get the return code
            return_code = process.poll()
            
            # Clean up the temporary file
            try:
                os.unlink(image_list_path)
            except:
                print("Warning: Failed to remove temporary file list")
            
            # Check if FFmpeg was successful
            if return_code != 0:
                error_output = process.stderr.read()
                error_msg = f"FFmpeg failed with code {return_code}: {error_output}"
                print(f"ERROR: {error_msg}")
                if progress_callback:
                    progress_callback(-1, error_msg)
                return False
            
            print(f"Successfully created video: {path}")
            return True
            
        except Exception as export_error:
            error_msg = f"Failed to create video: {str(export_error)}"
            print(f"ERROR: {error_msg}")
            if progress_callback:
                progress_callback(-1, error_msg)
            return False
        
        # Report cleanup progress
        if progress_callback:
            progress_callback(95, "Cleaning up temporary files")
            
        # Clean up temporary files
        try:
            for frame_file in frame_files:
                if os.path.exists(frame_file):
                    os.remove(frame_file)
            os.rmdir(temp_dir)
        except Exception as cleanup_error:
            print(f"Warning: Error during cleanup: {str(cleanup_error)}")
        
        # Final progress update
        if progress_callback:
            progress_callback(100, "Video export complete")
            
        return True
    except Exception as e:
        # Quiet optional MoviePy dependency warnings unless explicitly requested
        msg = str(e)
        if "No module named 'moviepy'" in msg and not os.environ.get('MOVIEPY_VERBOSE',''):
            # Soft notice for developers if debug flag set later, otherwise suppress
            pass
        else:
            print(f"Error exporting video: {msg}")
        import traceback
        traceback.print_exc()
        
        # Create a placeholder file to indicate error
        try:
            with open(path, 'w') as f:
                f.write(f"Error generating video: {str(e)}")
        except:
            pass
            
        if progress_callback:
            progress_callback(-1, f"Error: {msg}")
            
        return False