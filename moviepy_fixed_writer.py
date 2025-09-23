"""
Direct replacement for MoviePy's FFMPEG_VideoWriter that fixes the NoneType issue
"""

import os
import subprocess as sp
import numpy as np
import proglog

class FixedFFMPEG_VideoWriter:
    """
    A modified version of MoviePy's FFMPEG_VideoWriter that has fixes for handling 
    None values in fps parameter and progress callback.
    """
    
    def __init__(self, filename, size, fps, codec="libx264", 
                 preset="medium", bitrate=None, logfile=None, 
                 threads=None, ffmpeg_params=None):
        
        # Ensure fps is a valid number, default to 24 if None
        if fps is None:
            fps = 24.0
        elif not isinstance(fps, (int, float)):
            fps = float(fps)
        
        self.filename = filename
        self.codec = codec
        self.size = size
        self.fps = fps
        
        # Build the base FFmpeg command
        cmd = [
            'ffmpeg',
            '-y',  # overwrite output file if exists
            '-f', 'rawvideo',
            '-vcodec', 'rawvideo',
            '-s', '%dx%d' % (size[0], size[1]),  # size of image
            '-pix_fmt', 'rgb24',  # format
            '-r', '%.02f' % fps,  # frames per second
            '-i', '-',  # input comes from pipe
            '-an',  # no audio
        ]
        
        # Add codec parameters
        cmd.extend([
            '-vcodec', codec,
            '-preset', preset,
        ])
        
        # Add bitrate if specified
        if bitrate:
            cmd.extend(['-b:v', bitrate])
        
        # Add threads if specified
        if threads:
            cmd.extend(['-threads', str(threads)])
        
        # Add additional parameters if specified
        if ffmpeg_params:
            cmd.extend(ffmpeg_params)
        
        # Add output filename
        cmd.append(filename)
        
        # Open the subprocess
        self.proc = sp.Popen(cmd, stdin=sp.PIPE, 
                            stdout=sp.PIPE if logfile else None,
                            stderr=sp.PIPE if logfile else None)
        
    def write_frame(self, img_array):
        """
        Write a frame to the video file.
        """
        self.proc.stdin.write(img_array.tobytes())
        
    def close(self):
        """
        Close the video writer.
        """
        if self.proc:
            self.proc.stdin.close()
            if self.proc.stderr:
                self.proc.stderr.close()
            if self.proc.stdout:
                self.proc.stdout.close()
            self.proc.wait()
            self.proc = None

def write_video(clip, filename, fps=None, codec="libx264", bitrate=None,
               preset="medium", threads=None, ffmpeg_params=None, 
               write_logfile=False, verbose=True, logger="bar"):
    """
    A direct replacement for MoviePy's ffmpeg_write_video function
    that uses the FixedFFMPEG_VideoWriter.
    """
    # Make sure the fps is valid
    if fps is None:
        fps = getattr(clip, 'fps', 24)
        if fps is None:
            fps = 24
    
    # Get the size of the clip
    size = clip.size
    
    # Create the video writer
    writer = FixedFFMPEG_VideoWriter(
        filename, 
        size, 
        fps, 
        codec=codec, 
        preset=preset, 
        bitrate=bitrate, 
        threads=threads, 
        ffmpeg_params=ffmpeg_params
    )
    
    # Setup the progress logger
    logger = proglog.default_bar_logger(logger) if verbose else None
    
    # Total number of frames to process
    total_frames = int(clip.duration * fps)
    
    # Process each frame
    for t, frame in clip.iter_frames(fps=fps, logger=logger, total=total_frames):
        writer.write_frame(frame)
    
    # Close the writer
    writer.close()

def test_custom_writer():
    """
    Test the custom writer with a simple ImageClip
    """
    from moviepy.editor import ImageClip
    import numpy as np
    
    # Create a simple red frame
    red_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    red_frame[:, :, 0] = 255  # Full red
    
    # Create a clip with this single frame and set duration
    clip = ImageClip(red_frame).set_duration(5)  # 5 second duration
    print(f"Clip duration: {clip.duration}")
    print(f"Clip FPS: {getattr(clip, 'fps', None)}")
    
    # Set the fps attribute
    clip.fps = 24
    print(f"Clip FPS after setting: {clip.fps}")
    
    # Use our custom function to write video
    output_path = "custom_writer_output.mp4"
    write_video(clip, output_path, codec="libx264", ffmpeg_params=["-crf", "23"])
    print(f"Video written to {output_path}")

if __name__ == "__main__":
    test_custom_writer()