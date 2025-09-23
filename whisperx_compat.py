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
    print("❌ WhisperX not installed. Please install it with: pip install whisperx")
    original_whisperx = None

# Create a wrapper for the load_model function
def load_model(*args, **kwargs):
    """
    Wrapper for whisperx.load_model that handles PyTorch 2.6 compatibility.
    """
    if not original_whisperx:
        raise ImportError("WhisperX not installed")
        
    try:
        # Try with original function first
        return original_whisperx.load_model(*args, **kwargs)
    except Exception as e:
        # If it fails with a weights_only error, monkey patch torch.load
        if "weights_only" in str(e):
            print("⚠️ Detected PyTorch 2.6 compatibility issue. Applying unsafe workaround...")
            
            # Save the original torch.load
            original_torch_load = torch.load
            
            # Create a patched version that uses weights_only=False
            def patched_torch_load(f, *args, **kwargs):
                kwargs['weights_only'] = False
                print("🔧 Using patched torch.load with weights_only=False")
                return original_torch_load(f, *args, **kwargs)
            
            # Replace torch.load with our patched version
            torch.load = patched_torch_load
            
            try:
                # Try again with patched torch.load
                result = original_whisperx.load_model(*args, **kwargs)
                print("✅ Model loaded successfully with patched torch.load")
                return result
            finally:
                # Restore original torch.load
                torch.load = original_torch_load
        else:
            # Re-raise if it's not a weights_only error
            raise

# Create a wrapper for the load_align_model function
def load_align_model(*args, **kwargs):
    """
    Wrapper for whisperx.load_align_model that handles PyTorch 2.6 compatibility.
    """
    if not original_whisperx:
        raise ImportError("WhisperX not installed")
        
    try:
        # Try with original function first
        return original_whisperx.load_align_model(*args, **kwargs)
    except Exception as e:
        # If it fails with a weights_only error, monkey patch torch.load
        if "weights_only" in str(e):
            print("⚠️ Detected PyTorch 2.6 compatibility issue. Applying unsafe workaround...")
            
            # Save the original torch.load
            original_torch_load = torch.load
            
            # Create a patched version that uses weights_only=False
            def patched_torch_load(f, *args, **kwargs):
                kwargs['weights_only'] = False
                print("🔧 Using patched torch.load with weights_only=False")
                return original_torch_load(f, *args, **kwargs)
            
            # Replace torch.load with our patched version
            torch.load = patched_torch_load
            
            try:
                # Try again with patched torch.load
                result = original_whisperx.load_align_model(*args, **kwargs)
                print("✅ Model loaded successfully with patched torch.load")
                return result
            finally:
                # Restore original torch.load
                torch.load = original_torch_load
        else:
            # Re-raise if it's not a weights_only error
            raise

# Copy over the rest of the whisperx module
if original_whisperx:
    # Create a safer wrapper for align
    def align(*args, **kwargs):
        try:
            return original_whisperx.align(*args, **kwargs)
        except Exception as e:
            if "weights_only" in str(e):
                print("⚠️ Detected PyTorch 2.6 issue in align. Applying unsafe workaround...")
                original_torch_load = torch.load
                torch.load = lambda f, *a, **kw: original_torch_load(f, *a, weights_only=False, **kw)
                try:
                    result = original_whisperx.align(*args, **kwargs)
                    return result
                finally:
                    torch.load = original_torch_load
            else:
                raise
    
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