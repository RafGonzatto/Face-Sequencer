"""
Debug utility for MP4 export functionality
This script helps diagnose issues with the video export process
"""

import os
import sys
import time
import json
import traceback
from PIL import Image

# Add current directory to path
sys.path.insert(0, os.path.abspath('.'))

# Import our modules
from lipanim_core_demo import export_mp4, build_sequence

def create_test_frames(test_dir):
    """Create test frames for video export testing"""
    os.makedirs(test_dir, exist_ok=True)
    
    # Create basic test frames with different colors
    colors = {
        "red": (255, 0, 0),
        "green": (0, 255, 0),
        "blue": (0, 0, 255),
        "yellow": (255, 255, 0),
        "cyan": (0, 255, 255),
    }
    
    frame_paths = {}
    
    for color_name, rgb in colors.items():
        # Create a 100x100 colored image with specific size
        img = Image.new('RGB', (100, 100), color=rgb)
        img_path = os.path.join(test_dir, f"{color_name}.png")
        img.save(img_path)
        frame_paths[color_name[0].upper()] = img_path
        print(f"Created test frame: {img_path}")
    
    return frame_paths

def log_progress(progress, message=None):
    """Progress logging callback"""
    progress_str = f"{progress}%" if isinstance(progress, (int, float)) else str(progress)
    msg = f"{progress_str} - {message}" if message else progress_str
    print(f"PROGRESS: {msg}")

def debug_export():
    """Run a debug export with detailed logging"""
    print("\n===== MP4 EXPORT DEBUGGING =====\n")
    
    # Create test directory
    test_dir = os.path.abspath("debug_export")
    output_path = os.path.join(test_dir, "debug_output.mp4")
    
    # Create test frames
    print("Creating test frames...")
    frame_map = create_test_frames(test_dir)
    
    # Print detected MoviePy version
    try:
        import moviepy
        print(f"\nDetected MoviePy version: {moviepy.__version__}")
    except:
        print("\nCouldn't detect MoviePy version")
    
    # Create a simple sequence
    print("\nBuilding test sequence...")
    sequence = []
    
    # Add frames with explicit durations
    for char, frame_path in frame_map.items():
        # Verify frame exists
        if not os.path.exists(frame_path):
            print(f"WARNING: Frame path doesn't exist: {frame_path}")
            continue
            
        # Add frame to sequence with 500ms duration
        sequence.append({
            "char": char,
            "img": frame_path,
            "ms": 500  # 500ms duration per frame
        })
    
    # Print sequence details
    print(f"\nSequence contains {len(sequence)} frames:")
    for i, frame in enumerate(sequence):
        print(f"Frame {i}: char={frame['char']}, duration={frame['ms']}ms, path={frame['img']}")
        
        # Verify image dimensions
        try:
            with Image.open(frame['img']) as img:
                width, height = img.size
                print(f"  - Image size: {width}x{height}")
        except Exception as e:
            print(f"  - Error checking image: {e}")
    
    # Remove existing output file if it exists
    if os.path.exists(output_path):
        try:
            os.remove(output_path)
            print(f"\nRemoved existing output file: {output_path}")
        except Exception as e:
            print(f"\nError removing existing file: {e}")
    
    # Run the export with various quality settings
    for preset in ["medium", "fast"]:
        for crf in [23, 28]:
            test_output = f"{output_path[:-4]}_{preset}_crf{crf}.mp4"
            
            print(f"\n\nTesting export with preset={preset}, crf={crf}")
            print(f"Output: {test_output}")
            
            # Run the export
            try:
                start_time = time.time()
                
                success = export_mp4(
                    seq=sequence,
                    path=test_output,
                    fps=2,  # 2 FPS for 500ms frames
                    crf=crf,
                    preset=preset,
                    progress_callback=log_progress
                )
                
                end_time = time.time()
                duration = end_time - start_time
                
                print(f"\nExport completed in {duration:.2f} seconds")
                print(f"Success: {success}")
                
                if os.path.exists(test_output):
                    file_size = os.path.getsize(test_output)
                    print(f"Output file size: {file_size} bytes")
                    
                    if file_size < 1000:
                        print("WARNING: File size is suspiciously small!")
                else:
                    print("ERROR: Output file was not created!")
                    
            except Exception as e:
                print(f"\nEXCEPTION DURING EXPORT: {str(e)}")
                traceback.print_exc()
    
    print("\n===== DEBUG EXPORT COMPLETE =====")

if __name__ == "__main__":
    debug_export()