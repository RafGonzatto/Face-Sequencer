"""
Modified WhisperX import for PyTorch 2.6 compatibility.
This module provides a wrapper around the original WhisperX functions
to handle the PyTorch 2.6 compatibility issues.
"""

import os
import sys
import torch
import warnings
import importlib

# First try to import the original whisperx
try:
    import whisperx as original_whisperx
except ImportError:
    print("[X] WhisperX not installed. Please install it with: pip install whisperx")
    original_whisperx = None

from pytorch_compat import patched_load_context, is_problematic_version, ensure_whisperx_safe_globals

# Create a wrapper for the load_model function using new compatibility layer
def load_model(*args, **kwargs):
    if not original_whisperx:
        raise ImportError("WhisperX not installed")
    if is_problematic_version():
        ensure_whisperx_safe_globals()
        with patched_load_context():
            return original_whisperx.load_model(*args, **kwargs)
    return original_whisperx.load_model(*args, **kwargs)

# Create a wrapper for the load_align_model function
def load_align_model(*args, **kwargs):
    if not original_whisperx:
        raise ImportError("WhisperX not installed")
    if is_problematic_version():
        ensure_whisperx_safe_globals()
        with patched_load_context():
            return original_whisperx.load_align_model(*args, **kwargs)
    return original_whisperx.load_align_model(*args, **kwargs)

# Copy over the rest of the whisperx module
if original_whisperx:
    # Create a safer wrapper for align
    def align(*args, **kwargs):
        if is_problematic_version():
            ensure_whisperx_safe_globals()
            with patched_load_context():
                return original_whisperx.align(*args, **kwargs)
        return original_whisperx.align(*args, **kwargs)
    
    # Copy other attributes
    try:
        asr = original_whisperx.asr
    except AttributeError:
        pass
        
    try:
        diarize = original_whisperx.diarize
    except AttributeError:
        pass
        
    try:
        tokenize = original_whisperx.tokenize
    except AttributeError:
        pass
        
    try:
        utils = original_whisperx.utils
    except AttributeError:
        pass
        
    try:
        version = original_whisperx.__version__
    except AttributeError:
        version = "unknown"