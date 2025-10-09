# moviepy_compat.py - Compatibility fixes for MoviePy
import os
import sys
import importlib
import inspect

def patch_moviepy():
    """Apply compatibility patches for different MoviePy versions"""
    try:
        import moviepy
        from moviepy.editor import ImageSequenceClip
        
        print(f"Detected MoviePy version: {moviepy.__version__}")
        
        # Check if we're using a version with the problematic progress_bar parameter
        write_videofile_params = inspect.signature(ImageSequenceClip.write_videofile).parameters
        
        has_progress_bar = 'progress_bar' in write_videofile_params
        has_logger = 'logger' in write_videofile_params
        
        print(f"MoviePy compatibility: progress_bar={has_progress_bar}, logger={has_logger}")
        
        # For MoviePy 1.0.3 or similar versions lacking progress_bar
        if not has_progress_bar:
            def write_videofile_compat(self, filename, *args, **kwargs):
                # Remove unsupported parameters
                if 'progress_bar' in kwargs:
                    del kwargs['progress_bar']
                    
                # Call the original method with cleaned up kwargs
                return self._original_write_videofile(filename, *args, **kwargs)
            
            # Save the original method
            ImageSequenceClip._original_write_videofile = ImageSequenceClip.write_videofile
            
            # Replace with our compatible version
            ImageSequenceClip.write_videofile = write_videofile_compat
            
            print("[CHECK] Applied MoviePy compatibility patch for write_videofile")
        
        return True
        
    except Exception as e:
        print(f"[WARNING] Error applying MoviePy compatibility patches: {e}")
        return False

def get_compatible_write_params(filename, fps=30, codec='libx264', preset='medium', 
                               bitrate=None, audio=None, audio_fps=44100, 
                               audio_nbytes=2, audio_codec=None, audio_bitrate=None,
                               audio_bufsize=2000, temp_audiofile=None, 
                               remove_temp=True, write_logfile=False, verbose=True,
                               threads=None, ffmpeg_params=None, logger=None,
                               callback=None):
    """Generate compatible write_videofile parameters for the current MoviePy version"""
    import moviepy
    
    params = {
        'filename': filename,
        'fps': fps,
        'codec': codec,
        'preset': preset,
        'bitrate': bitrate,
        'audio': audio,
        'audio_fps': audio_fps,
        'audio_nbytes': audio_nbytes,
        'audio_codec': audio_codec,
        'audio_bitrate': audio_bitrate, 
        'audio_bufsize': audio_bufsize,
        'temp_audiofile': temp_audiofile,
        'remove_temp': remove_temp,
        'write_logfile': write_logfile,
        'verbose': verbose,
        'threads': threads,
        'ffmpeg_params': ffmpeg_params
    }
    
    # Filter out None values
    params = {k: v for k, v in params.items() if v is not None}
    
    # Add version-specific parameters
    try:
        from moviepy.editor import ImageSequenceClip
        write_videofile_params = inspect.signature(ImageSequenceClip.write_videofile).parameters
        
        if 'logger' in write_videofile_params and logger is not None:
            params['logger'] = logger
        
        if 'callback' in write_videofile_params and callback is not None:
            params['callback'] = callback
            
        if 'progress_bar' in write_videofile_params:
            params['progress_bar'] = False
    except:
        pass
        
    return params

# Apply patches if this module is imported
if __name__ != '__main__':
    patch_moviepy()