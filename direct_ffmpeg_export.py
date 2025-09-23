"""
Direct FFmpeg integration for exporting MP4 videos without relying on MoviePy's internals
"""
import os
import subprocess
import tempfile
from PIL import Image
import numpy as np

def export_image_sequence_to_mp4(image_paths, output_path, fps=24, crf=23, preset="medium", audio_path=None):
    """
    Export a sequence of images to an MP4 file using FFmpeg directly.
    
    Args:
        image_paths: List of image file paths
        output_path: Path to save the output MP4 file
        fps: Frames per second (default: 24)
        crf: Constant Rate Factor for quality (0-51, lower is better, default: 23)
        preset: FFmpeg preset (default: medium)
        audio_path: Optional audio file path to add to the video
    
    Returns:
        bool: True if successful, False otherwise
    """
    if not image_paths:
        print("Error: No images provided.")
        return False
    
    # Create a temporary directory for the image list
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        image_list_path = f.name
        for img_path in image_paths:
            # Write file paths for FFmpeg - normalize Windows paths
            normalized_path = img_path.replace('\\', '/')
            f.write(f'file \'{normalized_path}\'\n')
            f.write(f"duration {1/fps}\n")
        
        # Last image doesn't have duration
        normalized_path = image_paths[-1].replace('\\', '/')
        f.write(f'file \'{normalized_path}\'')
    
    try:
        # Build FFmpeg command
        cmd = [
            'ffmpeg',
            '-y',  # Overwrite output file
            '-f', 'concat',  # Use concat demuxer
            '-safe', '0',  # Don't check for absolute paths
            '-i', image_list_path,  # Input file list
            '-vf', f'fps={fps}',  # Force output framerate
            '-c:v', 'libx264',  # Use H.264 codec
            '-preset', preset,  # Encoding speed/compression tradeoff
            '-crf', str(crf),  # Quality level
            '-pix_fmt', 'yuv420p'  # Standard pixel format for compatibility
        ]
        
        # Add audio if provided
        if audio_path and os.path.exists(audio_path):
            cmd.extend(['-i', audio_path, '-c:a', 'aac', '-b:a', '192k'])
        else:
            cmd.append('-an')  # No audio
        
        # Add output path
        cmd.append(output_path)
        
        # Execute FFmpeg
        print("Running FFmpeg command:", ' '.join(cmd))
        process = subprocess.Popen(cmd, 
                                 stdout=subprocess.PIPE, 
                                 stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            print(f"FFmpeg error (code {process.returncode}):")
            print(stderr.decode('utf-8', errors='replace'))
            return False
        
        print(f"Successfully created video: {output_path}")
        return True
    
    finally:
        # Clean up the temporary file
        if os.path.exists(image_list_path):
            os.unlink(image_list_path)

def create_test_images(num_frames=24, output_dir=None):
    """
    Create a sequence of test images (color gradient)
    
    Args:
        num_frames: Number of frames to create
        output_dir: Directory to save the images (uses temp dir if None)
    
    Returns:
        list: Paths to the created images
    """
    if output_dir is None:
        output_dir = tempfile.mkdtemp()
    else:
        os.makedirs(output_dir, exist_ok=True)
    
    image_paths = []
    
    # Create a sequence of images with a color gradient
    width, height = 640, 480
    for i in range(num_frames):
        # Create a gradient image
        r = int(255 * (i / num_frames))
        image = np.zeros((height, width, 3), dtype=np.uint8)
        image[:, :, 0] = r  # Red gradient
        image[:, :, 1] = 255 - r  # Green gradient
        
        # Save the image
        img_path = os.path.join(output_dir, f"frame_{i:04d}.png")
        Image.fromarray(image).save(img_path)
        image_paths.append(img_path)
    
    return image_paths

def test_export():
    """
    Test the direct FFmpeg export with some test images
    """
    # Create test images
    print("Creating test images...")
    image_paths = create_test_images(num_frames=24)
    
    # Export to MP4
    print("Exporting to MP4...")
    output_path = "test_direct_ffmpeg.mp4"
    export_image_sequence_to_mp4(image_paths, output_path)
    
    # Clean up test images
    for path in image_paths:
        os.unlink(path)
    
    if os.path.dirname(image_paths[0]):
        os.rmdir(os.path.dirname(image_paths[0]))

if __name__ == "__main__":
    test_export()