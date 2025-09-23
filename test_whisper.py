# test_whisper.py - Test WhisperX with specific audio file
import os
import sys
import time
import numpy as np
import librosa

# Import the PyTorch 2.6 compatibility patch
try:
    from torch_patch import patch_torch_for_whisperx
    patch_torch_for_whisperx()
except ImportError:
    print("⚠️ Warning: torch_patch module not found, may encounter errors with PyTorch 2.6+")

import whisperx

def main():
    # File to test
    audio_file = "ElevenLabs_2025-09-22T18_53_43_Ethan_pre_sp100_s50_sb75_se0_b_m2.mp3"
    
    if not os.path.exists(audio_file):
        print(f"❌ Error: File {audio_file} not found in current directory")
        return
    
    print(f"🔍 Testing WhisperX with file: {audio_file}")
    print(f"📂 Full path: {os.path.abspath(audio_file)}")
    
    try:
        # Load audio using librosa (this is what the app uses)
        print("📊 Loading audio with librosa...")
        start_time = time.time()
        audio, sample_rate = librosa.load(audio_file, sr=16000, mono=True)
        print(f"✅ Audio loaded in {time.time() - start_time:.2f} seconds")
        print(f"   Sample rate: {sample_rate}, Duration: {len(audio) / sample_rate:.2f} seconds")
        
        # Load WhisperX model - using tiny model for fastest processing
        print("🔄 Loading WhisperX model (tiny)...")
        start_time = time.time()
        model = whisperx.load_model("tiny", device="cpu", compute_type="int8")
        print(f"✅ Model loaded in {time.time() - start_time:.2f} seconds")
        
        # Transcribe audio
        print("🎯 Transcribing audio...")
        start_time = time.time()
        result = model.transcribe(audio, batch_size=8)
        print(f"✅ Transcription completed in {time.time() - start_time:.2f} seconds")
        
        # Print transcription result
        print("\n📝 Transcription result:")
        print(result["text"])
        
        # Load alignment model
        print("\n🔄 Loading alignment model...")
        start_time = time.time()
        align_model, align_metadata = whisperx.load_align_model(language_code="pt", device="cpu")
        print(f"✅ Alignment model loaded in {time.time() - start_time:.2f} seconds")
        
        # Align audio
        print("🎯 Aligning audio...")
        start_time = time.time()
        aligned_result = whisperx.align(result["segments"], align_model, align_metadata, audio, "cpu", return_char_alignments=False)
        print(f"✅ Alignment completed in {time.time() - start_time:.2f} seconds")
        
        # Print word-level alignment
        print("\n📝 Word alignments:")
        for segment in aligned_result["segments"][:2]:  # Print just first 2 segments
            print(f"Segment: {segment['text']}")
            if "words" in segment:
                for word in segment["words"][:5]:  # Print just first 5 words per segment
                    print(f"  {word['word']}: {word['start']:.2f}s - {word['end']:.2f}s")
        
        print("\n✅ Test completed successfully!")
        return True
    
    except Exception as e:
        import traceback
        print(f"❌ Error: {str(e)}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)