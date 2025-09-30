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
from typing import Dict, Any, Optional, Callable

# Fix coverage/numba conflict before any imports
def _fix_coverage_conflict():
    """Temporarily disable coverage to avoid numba conflicts"""
    try:
        import os
        # Store and remove coverage environment variables that cause conflicts
        coverage_vars = ['COVERAGE_PROCESS_START', 'COV_CORE_SOURCE', 'COV_CORE_CONFIG']
        stored_vars = {}
        
        for var in coverage_vars:
            if var in os.environ:
                stored_vars[var] = os.environ[var]
                del os.environ[var]
        
        return stored_vars
    except Exception:
        return {}

def _restore_coverage_env(stored_vars):
    """Restore coverage environment variables"""
    try:
        import os
        for var, value in stored_vars.items():
            os.environ[var] = value
    except Exception:
        pass

# Apply the fix
_stored_coverage = _fix_coverage_conflict()

from logger import get_logger, log_exception
from audio_exceptions import AlignmentError, map_audio_processing_error
from config import config  # use configured allowed extensions

# Get logger for this module
audio_logger = get_logger('audio')

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


class AudioProcessingError(Exception):  # Deprecated shim
    """Deprecated legacy exception kept temporarily; raise AlignmentError instead."""
    def __init__(self, error_type, message, details=None):  # pragma: no cover
        self.error_type = error_type
        self.message = message
        self.details = details or {}
        super().__init__(message)

    def to_dict(self):  # pragma: no cover
        return {
            "error_type": getattr(self.error_type, 'value', str(self.error_type)),
            "message": self.message,
            "details": self.details,
        }


def handle_audio_errors(fallback_handler: Optional[Callable] = None):
    """
    Decorator for API endpoints to handle audio processing errors gracefully.
    
    Args:
        fallback_handler: Optional function to call for fallback behavior
                         Signature: fallback_handler(error, *args, **kwargs)
    """
    def decorator(func):
        # Get function-specific logger
        func_logger = get_logger(f"audio.{func.__module__}.{func.__name__}")
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Build context for logging
            context = {
                'function': func.__name__,
                'module': func.__module__
            }
            
            # Add request context if available
            try:
                from flask import request
                if request:
                    context.update({
                        'endpoint': request.endpoint,
                        'method': request.method,
                        'path': request.path,
                        'remote_addr': request.remote_addr
                    })
            except Exception:
                pass
                
            try:
                return func(*args, **kwargs)
            except AudioProcessingError as e:
                # Log the error with context
                log_exception(
                    func_logger, 
                    e, 
                    {
                        **context,
                        'error_type': e.error_type.value,
                        'details': e.details
                    }
                )

                # Try fallback if provided (allows custom response)
                if fallback_handler:
                    try:
                        func_logger.info(f"Trying fallback handler for {e.error_type.value}")
                        return fallback_handler(e, *args, **kwargs)
                    except Exception as fallback_error:
                        log_exception(
                            func_logger, 
                            fallback_error, 
                            {**context, 'phase': 'fallback_handler'}
                        )

                # Map error types to HTTP status codes
                status_map = {
                    AudioErrorType.UPLOAD_ERROR: 400,
                    AudioErrorType.FORMAT_ERROR: 415,
                    AudioErrorType.CORRUPT_FILE: 422,
                    AudioErrorType.ALIGNMENT_FAILED: 422,
                    AudioErrorType.PROCESSING_TIMEOUT: 504,
                    AudioErrorType.NO_SPEECH_DETECTED: 422,
                    AudioErrorType.LANGUAGE_UNSUPPORTED: 422,
                    AudioErrorType.SYSTEM_UNAVAILABLE: 503,
                }
                status_code = status_map.get(e.error_type, 400)

                # Build standardized error response (bridge to new hierarchy)
                from flask import jsonify
                try:
                    from api_responses import error_response  # Local import to avoid circular issues
                    # Map to new AlignmentError for unified structure if alignment related
                    mapped = map_audio_processing_error(e)
                    body = error_response(
                        mapped.args[0],
                        error_type=mapped.category,
                        status=status_code,
                        details={**e.details, **getattr(mapped, 'details', {})},
                        recommendations=getattr(mapped, 'recommendations', e.get_recommendations()),
                        lifecycle='alignment'
                    )
                except Exception as import_err:
                    log_exception(func_logger, import_err, {**context, 'phase': 'response_generation'})
                    # Fallback if helper import fails
                    body = {
                        "success": False,
                        "error": e.message,
                        "error_type": e.error_type.value,
                        "status": status_code,
                        "details": e.details,
                        "recommendations": e.get_recommendations(),
                    }

                return jsonify(body), status_code
            except AlignmentError as e:  # New unified exception support
                # Log with context
                log_exception(
                    func_logger,
                    e,
                    {**context, 'error_type': e.category, 'details': getattr(e, 'details', {})}
                )
                from flask import jsonify
                try:
                    from api_responses import error_response  # local import
                    body = error_response(
                        str(e),
                        error_type=e.category,
                        status=422,
                        details=getattr(e, 'details', {}),
                        recommendations=getattr(e, 'recommendations', []),
                        lifecycle='alignment'
                    )
                except Exception:
                    body = {
                        'success': False,
                        'error': str(e),
                        'error_type': e.category,
                        'status': 422,
                        'details': getattr(e, 'details', {}),
                    }
                return jsonify(body), 422
                
            except Exception as e:
                # Handle unexpected errors with full logging
                log_exception(func_logger, e, {**context, 'error_type': 'unexpected_error'})
                
                from flask import jsonify
                try:
                    from api_responses import error_response
                    body = error_response(
                        "An unexpected error occurred during audio processing",
                        error_type="unexpected_error",
                        status=500,
                        details={"error": str(e)},
                        lifecycle='alignment'
                    )
                except Exception as import_err:
                    log_exception(func_logger, import_err, {**context, 'phase': 'response_generation'})
                    body = {
                        "success": False,
                        "error": "An unexpected error occurred during audio processing",
                        "error_type": "unexpected_error",
                        "status": 500,
                        "details": {"error": str(e)},
                    }
                return jsonify(body), 500
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
        raise AlignmentError("No audio file provided", details={"field": "audio", 'legacy_error_type': 'upload_error'})
    
    # Check file extension
    filename = file.filename
    ext = os.path.splitext(filename)[1].lower().replace('.', '')
    
    # Use centrally configured set (includes webm/aac by default)
    try:
        allowed_extensions = set(config.limits.allowed_audio_extensions())  # type: ignore[arg-type]
    except Exception:
        # Fallback to a superset that includes webm to avoid false negatives
        allowed_extensions = {'wav', 'mp3', 'ogg', 'flac', 'm4a', 'aac', 'webm'}
    if ext not in allowed_extensions:
        raise AlignmentError("Unsupported audio format", details={"format": ext, "allowed_formats": list(allowed_extensions), 'legacy_error_type': 'format_error'})
    
    # Check if file is too large (over 50MB)
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    
    if file_size > 50 * 1024 * 1024:  # 50MB
        raise AlignmentError("Audio file is too large (max size: 50MB)", details={"file_size": file_size, "max_size": 50 * 1024 * 1024, 'legacy_error_type': 'upload_error'})
    
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
        raise AlignmentError("Failed to process audio file, it may be corrupted", details={"error_details": str(e), 'legacy_error_type': 'corrupt_file'})


def _detect_speech_activity_fallback(file_path):
    """
    Fallback speech detection using scipy and soundfile.
    
    Args:
        file_path: Path to the audio file
        
    Returns:
        dict: Basic speech activity information
    """
    try:
        import soundfile as sf
        import numpy as np
        from scipy import signal
        
        # Load audio with soundfile
        y, sr = sf.read(file_path)
        
        # Convert stereo to mono if necessary
        if len(y.shape) > 1:
            y = np.mean(y, axis=1)
        
        # Simple energy-based speech detection
        # Calculate RMS energy in windows
        window_size = int(0.025 * sr)  # 25ms windows
        hop_size = int(0.010 * sr)     # 10ms hop
        
        # Calculate windowed RMS
        energy = []
        for i in range(0, len(y) - window_size, hop_size):
            window = y[i:i + window_size]
            rms = np.sqrt(np.mean(window ** 2))
            energy.append(rms)
        
        energy = np.array(energy)
        
        # Check if audio has sufficient energy
        if np.mean(energy) < 0.01:
            raise AlignmentError("No speech detected in the audio file", 
                               details={"mean_energy": float(np.mean(energy)), 
                                      'legacy_error_type': 'no_speech_detected'})
        
        # Detect speech segments using simple threshold
        threshold = np.mean(energy) * 0.3
        speech_mask = energy > threshold
        
        # Find speech intervals
        speech_intervals = []
        in_speech = False
        start_time = 0
        
        for i, is_speech in enumerate(speech_mask):
            time = i * hop_size / sr
            
            if not in_speech and is_speech:
                in_speech = True
                start_time = time
            elif in_speech and not is_speech:
                in_speech = False
                speech_intervals.append({
                    "start": start_time,
                    "end": time,
                    "duration": time - start_time
                })
        
        # Close final interval if needed
        if in_speech:
            final_time = len(y) / sr
            speech_intervals.append({
                "start": start_time,
                "end": final_time,
                "duration": final_time - start_time
            })
        
        # Validate speech duration
        total_speech_duration = sum(interval["duration"] for interval in speech_intervals)
        if not speech_intervals or total_speech_duration < 0.3:
            raise AlignmentError("Insufficient speech detected in the audio file", 
                               details={"speech_duration": total_speech_duration, 
                                      'legacy_error_type': 'no_speech_detected'})
        
        return {
            "speech_intervals": speech_intervals,
            "total_speech_duration": total_speech_duration,
            "total_duration": len(y) / sr,
            "method": "fallback_scipy"
        }
        
    except AlignmentError:
        raise  # Pass through our errors
    except Exception as e:
        # If all else fails, just assume there's speech
        print(f"⚠️  Warning: Speech detection failed, assuming audio contains speech: {e}")
        return {
            "speech_intervals": [{"start": 0, "end": 1.0, "duration": 1.0}],
            "total_speech_duration": 1.0,
            "total_duration": 1.0,
            "method": "assumed"
        }


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
        # Try librosa import with conflict resolution
        try:
            # Temporarily disable coverage if it's interfering
            import os
            old_coverage = os.environ.get('COVERAGE_PROCESS_START')
            if old_coverage:
                os.environ.pop('COVERAGE_PROCESS_START', None)
            
            import librosa
            import numpy as np
            
            # Restore coverage setting
            if old_coverage:
                os.environ['COVERAGE_PROCESS_START'] = old_coverage
                
        except ImportError as import_err:
            # Fallback: Use simple audio analysis
            return _detect_speech_activity_fallback(file_path)
        
        # Load the audio file
        y, sr = librosa.load(file_path, sr=None)
        
        # Compute RMS energy
        rms = librosa.feature.rms(y=y)[0]
        
        # Check if audio has sufficient energy (not just silence)
        if np.mean(rms) < 0.01:
            raise AlignmentError("No speech detected in the audio file", details={"mean_energy": float(np.mean(rms)), 'legacy_error_type': 'no_speech_detected'})
        
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
            raise AlignmentError("Insufficient speech detected in the audio file", details={"speech_duration": total_speech_duration, 'legacy_error_type': 'no_speech_detected'})
        
        return {
            "speech_intervals": speech_intervals,
            "total_speech_duration": total_speech_duration,
            "total_duration": librosa.get_duration(y=y, sr=sr)
        }
    except AlignmentError:
        raise  # pass through unified errors
    except Exception as e:
        raise AlignmentError("Failed to analyze speech in the audio file", details={"error_details": str(e), 'legacy_error_type': 'processing_timeout'})


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