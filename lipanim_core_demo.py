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
            progress_callback(0, "Preparing frames")
        
        # Generate frames from sequence
        total_frames = len(seq)
        
        # First scan to determine optimal dimensions
        if progress_callback:
            progress_callback(5, "Scanning images for dimensions")
        
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
        
        # Second pass - generate and resize frames
        for i, frame in enumerate(seq):
            # Report progress periodically
            if progress_callback and i % max(1, total_frames // 20) == 0:
                progress_percent = int((i / total_frames) * 40)  # First 40% of progress is frame preparation
                progress_callback(progress_percent, f"Preparing frame {i+1}/{total_frames}")
            
            try:
                # For all frames, first try to get the image path from the frame data
                img_path = frame.get('img')
                
                # Check for any type of frame that should use fallback image
                fallback_needed = False
                
                # 1. Is it a pause frame without an image?
                if frame.get('is_pause', False) and not img_path:
                    fallback_needed = True
                
                # 2. Is it a symbol fallback frame?
                if frame.get('is_symbol_fallback', False):
                    fallback_needed = True
                    
                # 3. Does the frame not have a valid image?
                if not img_path or not os.path.exists(img_path):
                    fallback_needed = True
                
                # If fallback needed, try to get it
                if fallback_needed:
                    fallback_img_path = frame.get('fallback_img')
                    if fallback_img_path and os.path.exists(fallback_img_path):
                        img_path = fallback_img_path
                        frame_type = "pause" if frame.get('is_pause', False) else "symbol"
                        print(f"Using fallback image for {frame_type} frame {i}: {img_path}")
                
                # After trying fallback, if still no valid image, use an existing image from our folders
                if not img_path or not os.path.exists(img_path):
                    # Try each possible folder for fallbacks in order of preference
                    default_fallback = None
                    potential_folders = [
                        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'images'),
                        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'debug_export'),
                        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'outros')
                    ]
                    
                    # Try each folder until we find a usable image
                    for folder in potential_folders:
                        if os.path.exists(folder):
                            image_files = [f for f in os.listdir(folder) 
                                          if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp'))]
                            if image_files:
                                default_fallback = os.path.join(folder, image_files[0])
                                print(f"Using default fallback image from {folder}: {default_fallback}")
                                break
                    
                    if default_fallback and os.path.exists(default_fallback):
                        img_path = default_fallback
                        print(f"Using existing image as fallback for frame {i}: {img_path}")
                    else:
                        # As last resort, create a warning frame
                        print(f"WARNING: Missing image and fallback for frame {i} (char: {frame.get('char', '?')})")
                        img = np.zeros((max_height, max_width, 4), dtype=np.uint8)
                        # Use magenta background to make it obvious this is an error condition
                        img[:, :, 0] = 255  # Red
                        img[:, :, 2] = 255  # Blue
                else:
                    try:
                        # Load and convert to numpy array with standardized dimensions
                        pil_img = Image.open(img_path).convert('RGBA')
                        
                        # Check if image needs resizing for standardization
                        current_width, current_height = pil_img.size
                        if current_width != max_width or current_height != max_height:
                            print(f"Resizing frame {i} from {current_width}x{current_height} to {max_width}x{max_height}")
                            
                            # Create a blank image with standard dimensions
                            new_img = Image.new('RGBA', (max_width, max_height), (0, 0, 0, 0))
                            
                            # Calculate position to center the original image
                            paste_x = (max_width - current_width) // 2
                            paste_y = (max_height - current_height) // 2
                            
                            # Paste the original image onto the blank canvas
                            new_img.paste(pil_img, (paste_x, paste_y), pil_img)
                            pil_img = new_img
                            
                        # Convert to numpy array
                        img = np.array(pil_img)
                    except Exception as e:
                        print(f"Error processing image {img_path}: {str(e)}")
                        # Create a blank frame with error message on failure
                        img = np.zeros((max_height, max_width, 4), dtype=np.uint8)
                        # Try to add error text
                        try:
                            error_img = Image.fromarray(img)
                            draw = ImageDraw.Draw(error_img)
                            draw.text((20, 20), f"Error: {str(e)}", fill=(255, 0, 0, 255))
                            img = np.array(error_img)
                        except:
                            pass
            except Exception as e:
                print(f"Error processing frame {i}: {str(e)}")
                # Create a placeholder frame on error
                img = np.zeros((480, 640, 4), dtype=np.uint8)
                # Add error text if possible
                try:
                    from PIL import Image, ImageDraw, ImageFont
                    error_img = Image.fromarray(img)
                    draw = ImageDraw.Draw(error_img)
                    draw.text((20, 20), f"Error: {str(e)}", fill=(255, 0, 0, 255))
                    img = np.array(error_img)
                except:
                    pass
            
            # Save frame to temp directory
            from PIL import Image
            frame_path = os.path.join(temp_dir, f"frame_{i:05d}.png")
            frame_files.append(frame_path)
            Image.fromarray(img).save(frame_path)
            
            # Calculate frame duration based on sequence
            # Default to 100ms if not specified
            frame_duration = frame.get('ms', 100) / 1000.0  # Convert ms to seconds
            if frame_duration <= 0:
                print(f"Warning: Invalid duration for frame {i}, using default")
                frame_duration = 0.1  # Default to 100ms
            
            # Duplicate the frame to achieve the desired duration at the given FPS
            frame_count = max(1, int(round(frame_duration * fps)))
            
            # Repeat the frame path in the list to achieve the correct duration
            if frame_count > 1:
                frame_files.extend([frame_path] * (frame_count - 1))
        
        # Report progress
        if progress_callback:
            progress_callback(40, "Creating video clip")
        
        # Verify all frames have the same dimensions before creating the clip
        if progress_callback:
            progress_callback(45, "Verifying frame consistency")
        
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
            
            # Report progress
            if progress_callback:
                progress_callback(50, "Starting video encoding with FFmpeg")
            
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
            
            # Monitor FFmpeg progress
            last_progress = 0
            while True:
                output_line = process.stderr.readline()
                if output_line == '' and process.poll() is not None:
                    break
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
                            
                            # Only update if progress has changed
                            if progress_percent > last_progress:
                                last_progress = progress_percent
                                if progress_callback:
                                    progress_callback(progress_percent, f"Encoding video: {int((seconds / total_duration) * 100)}%")
                        except:
                            # If we can't parse progress, still show that we're working
                            if progress_callback and (last_progress < 75):
                                last_progress = 75
                                progress_callback(75, "Encoding video (progress estimation error)")
            
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
        print(f"Error exporting video: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Create a placeholder file to indicate error
        try:
            with open(path, 'w') as f:
                f.write(f"Error generating video: {str(e)}")
        except:
            pass
            
        if progress_callback:
            progress_callback(-1, f"Error: {str(e)}")
            
        return False