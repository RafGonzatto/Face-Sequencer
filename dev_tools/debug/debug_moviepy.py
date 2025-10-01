"""
Test script to debug MoviePy version-specific issues
"""
import os
import sys
import traceback

try:
    import moviepy
    print(f"MoviePy version: {moviepy.__version__}")
    
    from moviepy.editor import ImageSequenceClip, ImageClip
    import numpy as np
    
    # Create a simple test clip
    print("\nCreating test clip...")
    
    # Create a simple red frame
    red_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    red_frame[:, :, 0] = 255  # Full red
    
    # Create a clip with this single frame and set duration
    clip = ImageClip(red_frame).set_duration(5)  # 5 second duration
    print(f"Clip duration: {clip.duration}")
    
    # Print out all parameters for write_videofile
    import inspect
    write_sig = inspect.signature(clip.write_videofile)
    print("\nwrite_videofile signature:")
    for param_name, param in write_sig.parameters.items():
        print(f"  {param_name}: {param.default}")
    
    # Custom progress callback that is defensive against None values
    def safe_progress_callback(t=None, remaining=None, **kwargs):
        try:
            if t is None:
                t = 0
            if remaining is None:
                remaining = 0
            
            progress = (t / (t + remaining + 0.00001)) * 100  # avoid division by zero
            sys.stdout.write(f"\rProgress: {progress:.1f}%")
            sys.stdout.flush()
        except Exception as e:
            print(f"\nCallback error: {str(e)}")
        return 0  # Always return 0 to continue
    
    # Try writing with different parameter combinations
    output_path = "test_moviepy_output.mp4"
    
    # Let's manually set clip.fps
    clip.fps = 24
    print(f"Clip FPS explicitly set to: {clip.fps}")
    
    # Try with basic parameters
    print("\nTrying with basic parameters...")
    try:
        clip.write_videofile(output_path, codec="libx264", audio=False, 
                            verbose=False)
        print("\n✓ Success with basic parameters!")
    except Exception as e:
        print(f"\n✗ Failed with basic parameters: {str(e)}")
        traceback.print_exc()
    
    # Try with ffmpeg_params
    print("\nTrying with ffmpeg_params...")
    try:
        clip.write_videofile(output_path, codec="libx264", audio=False, 
                            verbose=False, 
                            ffmpeg_params=["-crf", "23"])
        print("\n✓ Success with ffmpeg_params!")
    except Exception as e:
        print(f"\n✗ Failed with ffmpeg_params: {str(e)}")
        traceback.print_exc()
    
    # Try with bitrate
    print("\nTrying with bitrate...")
    try:
        clip.write_videofile(output_path, codec="libx264", audio=False, 
                            verbose=False, 
                            bitrate="2000k")
        print("\n✓ Success with bitrate!")
    except Exception as e:
        print(f"\n✗ Failed with bitrate: {str(e)}")
        traceback.print_exc()
    
    # Try with logger=None
    print("\nTrying with logger=None...")
    try:
        clip.write_videofile(output_path, codec="libx264", audio=False,
                            verbose=True, logger=None)
        print("\n✓ Success with logger=None!")
    except Exception as e:
        print(f"\n✗ Failed with logger=None: {str(e)}")
        traceback.print_exc()
    
except ImportError as e:
    print(f"Error importing MoviePy: {str(e)}")
    sys.exit(1)
except Exception as e:
    print(f"Unexpected error: {str(e)}")
    traceback.print_exc()
    sys.exit(1)