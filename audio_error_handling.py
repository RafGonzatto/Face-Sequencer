# audio_error_handling.py - Enhanced error handling for audio processing
"""
This module provides improved error handling for audio processing in Face Sequencer Pro.
It implements graceful fallbacks and user-friendly error messages when audio processing fails.
"""

import os
import time
import tempfile
import traceback
from functools import wraps
from enum import Enum

class AudioErrorType(Enum):
    """Types of errors that can occur during audio processing"""
    UPLOAD_ERROR = "upload_error"
    FORMAT_ERROR = "format_error"
    CORRUPT_FILE = "corrupt_file"
    ALIGNMENT_FAILED = "alignment_failed"
    PROCESSING_TIMEOUT = "processing_timeout"
    NO_SPEECH_DETECTED = "no_speech_detected"
    LANGUAGE_UNSUPPORTED = "language_unsupported"
    SYSTEM_UNAVAILABLE = "system_unavailable"


class AudioProcessingError(Exception):
    """Custom exception for audio processing errors"""
    
    def __init__(self, error_type, message, details=None):
        """Initialize with error type, message, and optional details"""
        self.error_type = error_type
        self.message = message
        self.details = details or {}
        super().__init__(message)

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "error_type": self.error_type.value,
            "message": self.message,
            "details": self.details,
            "recommendations": self.get_recommendations()
        }

    def get_recommendations(self):
        """Get user-friendly recommendations based on error type"""
        recommendations = {
            AudioErrorType.UPLOAD_ERROR: [
                "Try uploading a smaller file (under 20MB)",
                "Check your internet connection",
                "Try a different audio file"
            ],
            AudioErrorType.FORMAT_ERROR: [
                "Convert your file to WAV, MP3, OGG, or FLAC format",
                "Try using a standard audio editing tool to resave the file"
            ],
            AudioErrorType.CORRUPT_FILE: [
                "Your audio file appears to be corrupted",
                "Try re-encoding it with an audio editor",
                "Record a new audio file if possible"
            ],
            AudioErrorType.ALIGNMENT_FAILED: [
                "Make sure your text matches what is spoken in the audio",
                "Try using shorter, clearer audio with less background noise",
                "Fall back to manual timing mode"
            ],
            AudioErrorType.PROCESSING_TIMEOUT: [
                "Try a shorter audio file (under 60 seconds)",
                "Try again when the server is less busy",
                "Fall back to manual timing mode"
            ],
            AudioErrorType.NO_SPEECH_DETECTED: [
                "Ensure your audio file contains clear speech",
                "Check the audio volume and make sure it's not too quiet",
                "Try removing background noise or music"
            ],
            AudioErrorType.LANGUAGE_UNSUPPORTED: [
                "Currently supported languages are: English (en-US) and Portuguese (pt-BR)",
                "Try providing audio in one of these languages"
            ],
            AudioErrorType.SYSTEM_UNAVAILABLE: [
                "The audio alignment system is currently unavailable",
                "Fall back to manual timing mode",
                "Try again later when the system is back online"
            ]
        }
        return recommendations.get(self.error_type, ["Try again with a different file"])


def handle_audio_errors(fallback_handler=None):
    """
    Decorator for API endpoints to handle audio processing errors gracefully.
    
    Args:
        fallback_handler: Optional function to call for fallback behavior
                         Signature: fallback_handler(error, *args, **kwargs)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except AudioProcessingError as e:
                # Log the error
                print(f"Audio processing error: {e.error_type.value} - {e.message}")
                
                # Try fallback if provided
                if fallback_handler:
                    try:
                        return fallback_handler(e, *args, **kwargs)
                    except Exception as fallback_error:
                        print(f"Fallback handler failed: {str(fallback_error)}")
                
                # Return error response
                from flask import jsonify
                return jsonify({
                    "success": False,
                    "error": e.message,
                    "error_info": e.to_dict(),
                    "fallback_attempted": fallback_handler is not None
                }), 400
            except Exception as e:
                # Handle unexpected errors
                print(f"Unexpected error in audio processing: {str(e)}")
                print(traceback.format_exc())
                
                # Return a generic error response
                from flask import jsonify
                return jsonify({
                    "success": False,
                    "error": "An unexpected error occurred during audio processing",
                    "error_details": str(e)
                }), 500
        return wrapper
    return decorator


def validate_audio_file(file):
    """
    Validate an audio file to ensure it can be processed.
    
    Args:
        file: The file object to validate
        
    Raises:
        AudioProcessingError: If the file is invalid
        
    Returns:
        True if validation passed
    """
    if not file or not hasattr(file, 'filename'):
        raise AudioProcessingError(
            AudioErrorType.UPLOAD_ERROR,
            "No audio file provided",
            {"field": "audio"}
        )
    
    # Check file extension
    filename = file.filename
    ext = os.path.splitext(filename)[1].lower().replace('.', '')
    
    allowed_extensions = {'wav', 'mp3', 'ogg', 'flac', 'm4a'}
    if ext not in allowed_extensions:
        raise AudioProcessingError(
            AudioErrorType.FORMAT_ERROR,
            f"Unsupported audio format: {ext}",
            {"format": ext, "allowed_formats": list(allowed_extensions)}
        )
    
    # Check if file is too large (over 50MB)
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    
    if file_size > 50 * 1024 * 1024:  # 50MB
        raise AudioProcessingError(
            AudioErrorType.UPLOAD_ERROR,
            "Audio file is too large (max size: 50MB)",
            {"file_size": file_size, "max_size": 50 * 1024 * 1024}
        )
    
    return True


def validate_audio_content(file_path):
    """
    Validate audio content to ensure it contains valid audio data.
    
    Args:
        file_path: Path to the audio file to validate
        
    Raises:
        AudioProcessingError: If the audio content is invalid
        
    Returns:
        dict: Audio metadata if validation passed
    """
    try:
        # Try to open with soundfile (for WAV, FLAC, OGG)
        import soundfile as sf
        try:
            info = sf.info(file_path)
            return {
                "duration_ms": info.duration * 1000,
                "sample_rate": info.samplerate,
                "channels": info.channels,
                "format": info.format
            }
        except Exception:
            # If soundfile fails, try librosa as a backup
            import librosa
            y, sr = librosa.load(file_path, sr=None)
            duration = librosa.get_duration(y=y, sr=sr)
            
            return {
                "duration_ms": duration * 1000,
                "sample_rate": sr,
                "channels": 1 if len(y.shape) == 1 else y.shape[0],
                "format": os.path.splitext(file_path)[1].replace('.', '')
            }
    except Exception as e:
        raise AudioProcessingError(
            AudioErrorType.CORRUPT_FILE,
            "Failed to process audio file, it may be corrupted",
            {"error_details": str(e)}
        )


def detect_speech_activity(file_path):
    """
    Detect if there is speech in the audio file.
    
    Args:
        file_path: Path to the audio file
        
    Raises:
        AudioProcessingError: If no speech is detected
        
    Returns:
        dict: Information about detected speech
    """
    try:
        import librosa
        import numpy as np
        
        # Load the audio file
        y, sr = librosa.load(file_path, sr=None)
        
        # Compute RMS energy
        rms = librosa.feature.rms(y=y)[0]
        
        # Check if audio has sufficient energy (not just silence)
        if np.mean(rms) < 0.01:
            raise AudioProcessingError(
                AudioErrorType.NO_SPEECH_DETECTED,
                "No speech detected in the audio file",
                {"mean_energy": float(np.mean(rms))}
            )
        
        # Detect speech segments
        speech_intervals = []
        threshold = np.mean(rms) * 0.5
        is_speech = False
        speech_start = 0
        
        for i, energy in enumerate(rms):
            frame_time = librosa.frames_to_time(i, sr=sr)
            
            if not is_speech and energy > threshold:
                # Start of speech
                is_speech = True
                speech_start = frame_time
            elif is_speech and energy <= threshold:
                # End of speech
                is_speech = False
                speech_intervals.append({
                    "start": speech_start,
                    "end": frame_time,
                    "duration": frame_time - speech_start
                })
        
        # Close any open interval
        if is_speech:
            frame_time = librosa.frames_to_time(len(rms) - 1, sr=sr)
            speech_intervals.append({
                "start": speech_start,
                "end": frame_time,
                "duration": frame_time - speech_start
            })
        
        # If we found no intervals or very short total duration, raise error
        total_speech_duration = sum(interval["duration"] for interval in speech_intervals)
        if not speech_intervals or total_speech_duration < 0.5:
            raise AudioProcessingError(
                AudioErrorType.NO_SPEECH_DETECTED,
                "Insufficient speech detected in the audio file",
                {"speech_duration": total_speech_duration}
            )
        
        return {
            "speech_intervals": speech_intervals,
            "total_speech_duration": total_speech_duration,
            "total_duration": librosa.get_duration(y=y, sr=sr)
        }
    except AudioProcessingError:
        # Re-raise specific errors
        raise
    except Exception as e:
        # Convert general errors to AudioProcessingError
        raise AudioProcessingError(
            AudioErrorType.PROCESSING_TIMEOUT,
            "Failed to analyze speech in the audio file",
            {"error_details": str(e)}
        )


def with_timeout(timeout_seconds=30):
    """
    Decorator to add timeout to a function.
    
    Args:
        timeout_seconds: Maximum execution time in seconds
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            import threading
            import queue
            
            result_queue = queue.Queue()
            exception_queue = queue.Queue()
            
            def target():
                try:
                    result = func(*args, **kwargs)
                    result_queue.put(result)
                except Exception as e:
                    exception_queue.put(e)
            
            thread = threading.Thread(target=target)
            thread.daemon = True
            thread.start()
            thread.join(timeout_seconds)
            
            if thread.is_alive():
                # Timeout occurred
                raise AudioProcessingError(
                    AudioErrorType.PROCESSING_TIMEOUT,
                    f"Processing timed out after {timeout_seconds} seconds",
                    {"timeout": timeout_seconds}
                )
            
            if not exception_queue.empty():
                # Re-raise any exception from the thread
                raise exception_queue.get()
            
            if not result_queue.empty():
                return result_queue.get()
            else:
                # This should not happen if the thread completed without exception
                raise AudioProcessingError(
                    AudioErrorType.PROCESSING_TIMEOUT,
                    "Processing completed but no result was returned",
                    {"timeout": timeout_seconds}
                )
        return wrapper
    return decorator


class AudioFallbackHandler:
    """Provides fallback behaviors when audio processing fails"""
    
    @staticmethod
    def fallback_to_manual_timing(error, *args, **kwargs):
        """
        Fall back to manual timing when audio alignment fails.
        
        Args:
            error: The AudioProcessingError that occurred
            *args, **kwargs: Original function arguments
            
        Returns:
            dict: Response with fallback sequence and warning
        """
        from flask import jsonify
        
        # Extract text from the request (assumes it's in kwargs or can be found)
        text = kwargs.get('text', '')
        if not text and len(args) > 0:
            # Try to get text from the first argument if it's a dict
            if isinstance(args[0], dict):
                text = args[0].get('text', '')
        
        # Build sequence with manual timing
        from lipanim_core_demo import build_sequence
        try:
            # Try to get settings from the current project
            from flask import current_app
            settings = current_app.config.get('app_state', {}).get('current_project', {}).get('settings', {})
            frame_duration = settings.get('frame_duration', 80)
            pause_duration = settings.get('pause_duration', 120)
            
            # Build sequence with manual timing using corrected parameters
            sequence = build_sequence(
                text=text,
                letter_map={},  # Will use defaults
                dur_ms=frame_duration,
                gap_ms=pause_duration
            )
            
            return jsonify({
                "success": True,
                "fallback_to_manual": True,
                "original_error": error.to_dict(),
                "sequence": sequence,
                "warning": "Audio-driven timing failed. Falling back to manual timing."
            })
        except Exception as e:
            # If fallback also fails, return both errors
            return jsonify({
                "success": False,
                "error": "Both audio-driven and manual timing failed",
                "audio_error": error.to_dict(),
                "fallback_error": str(e)
            }), 500