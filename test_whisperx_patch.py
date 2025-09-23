# test_whisperx_patch.py - Test PyTorch 2.6 compatibility patch for WhisperX
import os
import sys
import torch

print(f"🔍 Testing PyTorch patch for WhisperX")
print(f"📊 PyTorch version: {torch.__version__}")

# First import the patch
from torch_patch import patch_torch_for_whisperx
patch_torch_for_whisperx()

print(f"✅ Successfully imported torch_patch module")

# Now try to import whisperx
try:
    import whisperx
    print(f"✅ Successfully imported whisperx")
    
    # Try loading a model
    print(f"🔄 Attempting to load alignment model...")
    
    # Use a very small device batch size to minimize memory usage
    model = whisperx.load_model("tiny", "cpu", compute_type="int8")
    print(f"✅ Successfully loaded transcription model")
    
    # Try loading alignment model
    align_model, align_metadata = whisperx.load_align_model(language_code="pt", device="cpu")
    print(f"✅ Successfully loaded alignment model")
    
    print(f"🎉 All models loaded successfully! The patch works.")
    
except Exception as e:
    print(f"❌ Error: {e}")
    print(f"💡 Debug details: {type(e).__name__}")

print("Test completed.")