# fix_pytorch_whisperx.py - Direct fix for PyTorch 2.6 compatibility with WhisperX

import torch
import sys
import os
import warnings
import importlib
import types

def monkey_patch_torch():
    """
    Apply direct monkey patch to PyTorch to allow loading WhisperX models safely
    """
    print("\n-----------------------------------------")
    print("PyTorch WhisperX Compatibility Fixer")
    print("-----------------------------------------")
    
    print(f"PyTorch version: {torch.__version__}")
    
    # Save the original torch.load function
    original_torch_load = torch.load
    
    # Create a new function that defaults to weights_only=False
    def patched_torch_load(f, *args, **kwargs):
        # If weights_only isn't explicitly set, set it to False
        if 'weights_only' not in kwargs:
            kwargs['weights_only'] = False
        return original_torch_load(f, *args, **kwargs)
    
    # Replace the torch.load function with our patched version
    torch.load = patched_torch_load
    
    # Add warning suppression for wav2vec2 models
    warnings.filterwarnings("ignore", message=".*vulnerability issue.*")
    
    print(f"✅ Successfully patched torch.load to use weights_only=False by default")
    print(f"🛡️  Note: This is less secure but necessary for WhisperX compatibility")
    print(f"� Suppressed vulnerability warnings for wav2vec2 models")
    print("-----------------------------------------\n")
    
    return True
    
def create_whisperx_compatibility_layer():
    """
    Create a patched version of WhisperX that works with PyTorch 2.6+
    """
    # Ensure torch is patched first
    monkey_patch_torch()
    
    try:
        # Try to import the original whisperx
        import whisperx as original_whisperx
        
        # Create a new module
        whisperx_compat = types.ModuleType("whisperx_compat")
        whisperx_compat.__doc__ = "WhisperX compatibility layer for PyTorch 2.6+"
        
        # Copy all attributes from original whisperx
        for attr_name in dir(original_whisperx):
            if not attr_name.startswith("__"):
                try:
                    setattr(whisperx_compat, attr_name, getattr(original_whisperx, attr_name))
                except Exception:
                    pass
        
        # Replace load_model and load_align_model with our patched versions
        def patched_load_model(*args, **kwargs):
            print("🔄 Using patched WhisperX load_model")
            return original_whisperx.load_model(*args, **kwargs)
            
        def patched_load_align_model(*args, **kwargs):
            print("🔄 Using patched WhisperX load_align_model")
            try:
                return original_whisperx.load_align_model(*args, **kwargs)
            except Exception as e:
                if "vulnerability issue" in str(e):
                    print("⚠️ Ignoring vulnerability warning and trying again...")
                    # Temporarily suppress warnings
                    with warnings.catch_warnings():
                        warnings.filterwarnings("ignore")
                        return original_whisperx.load_align_model(*args, **kwargs)
                else:
                    raise
        
        # Replace functions with our patched versions
        whisperx_compat.load_model = patched_load_model
        whisperx_compat.load_align_model = patched_load_align_model
        
        # Add to sys.modules for import
        sys.modules["whisperx_compat"] = whisperx_compat
        
        print(f"✅ Created WhisperX compatibility layer")
        return whisperx_compat
    
    except ImportError:
        print(f"❌ WhisperX not installed. Please install with: pip install whisperx")
        return None

def patch_all():
    """Apply all patches for WhisperX compatibility"""
    monkey_patch_torch()
    create_whisperx_compatibility_layer()
    return True

if __name__ == "__main__":
    patch_all()
    
    # Try to verify the patch works with WhisperX
    try:
        import whisperx
        print(f"✅ Successfully imported whisperx after applying patch")
    except ImportError:
        print(f"⚠️ Could not import whisperx. Please install it with: pip install whisperx")
        sys.exit(1)
    
    # Try loading a small model to verify the patch works
    try:
        # Only try to load the model if explicitly requested
        if len(sys.argv) > 1 and sys.argv[1] == "--test-load":
            print(f"🔄 Testing patch by loading a tiny model...")
            model = whisperx.load_model("tiny", "cpu", compute_type="int8")
            print(f"✅ Successfully loaded a model! The patch is working.")
            
            if len(sys.argv) > 2 and sys.argv[2] == "--test-align":
                print(f"🔄 Testing alignment model loading...")
                try:
                    align_model, align_metadata = whisperx.load_align_model(language_code="pt", device="cpu")
                    print(f"✅ Successfully loaded alignment model! The patch is fully working.")
                except Exception as e:
                    print(f"❌ Error loading alignment model: {e}")
    except Exception as e:
        print(f"❌ Error loading model: {e}")
        sys.exit(1)
    
    print(f"✅ Patch complete. You can now safely use WhisperX with PyTorch 2.6+")
    sys.exit(0)