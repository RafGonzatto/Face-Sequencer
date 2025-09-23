# test_whisperx_compat.py - Test PyTorch 2.6 compatibility with our whisperx_compat module
import os
import sys
import torch

print(f"🔍 Testing WhisperX compatibility module")
print(f"📊 PyTorch version: {torch.__version__}")

# Import our compatibility module instead of whisperx
try:
    import whisperx_compat as whisperx
    print(f"✅ Successfully imported whisperx_compat module")
    
    # Try loading a model
    print(f"🔄 Attempting to load transcription model...")
    model = whisperx.load_model("tiny", "cpu", compute_type="int8")
    print(f"✅ Successfully loaded transcription model")
    
    # Try loading alignment model
    print(f"🔄 Attempting to load alignment model...")
    align_model, align_metadata = whisperx.load_align_model(language_code="pt", device="cpu")
    print(f"✅ Successfully loaded alignment model")
    
    print(f"🎉 All models loaded successfully! The compatibility layer works.")
    
except Exception as e:
    print(f"❌ Error: {e}")
    print(f"💡 Debug details: {type(e).__name__}")

print("Test completed.")