# whisperx_test.py - Direct test of WhisperX with ElevenLabs audio
import os
import sys
import time
import numpy as np
import librosa

# Apply direct PyTorch patch
try:
    import torch
    if hasattr(torch, "__version__"):
        version = torch.__version__
        if version.startswith("2.6") or version.startswith("2.7"):
            # Override torch.load to always use weights_only=False for compatibility
            original_torch_load = torch.load
            def patched_torch_load(f, *args, **kwargs):
                # Always use weights_only=False regardless of what's passed
                kwargs_copy = {k: v for k, v in kwargs.items() if k != 'weights_only'}
                kwargs_copy['weights_only'] = False
                print("🔄 Using patched torch.load with weights_only=False")
                return original_torch_load(f, *args, **kwargs_copy)
            
            # Apply the patch
            torch.load = patched_torch_load
            print(f"✅ PyTorch {version} patched for WhisperX compatibility")
except Exception as e:
    print(f"⚠️ Failed to apply PyTorch patch: {e}")

import whisperx

def main():
    # File to test
    audio_file = "test_audio.mp3"
    
    if not os.path.exists(audio_file):
        print(f"❌ Error: File {audio_file} not found in current directory")
        return False
    
    print(f"🔍 Testing WhisperX directly with file: {audio_file}")
    print(f"📂 Full path: {os.path.abspath(audio_file)}")
    
    try:
        # Load audio file with librosa
        print("📊 Loading audio with librosa...")
        start_time = time.time()
        audio, sample_rate = librosa.load(audio_file, sr=16000, mono=True)
        print(f"✅ Audio loaded in {time.time() - start_time:.2f} seconds")
        print(f"   Sample rate: {sample_rate}, Duration: {len(audio) / sample_rate:.2f} seconds")
        
        # Process audio
        print("📊 Processing audio...")
        rms = np.sqrt(np.mean(audio**2))
        print(f"   Original RMS level: {rms:.4f}")
        
        # Apply normalization
        audio = librosa.util.normalize(audio) * 0.95
        rms_after = np.sqrt(np.mean(audio**2))
        print(f"   Normalized RMS level: {rms_after:.4f}")
        
        # Apply preemphasis
        audio = librosa.effects.preemphasis(audio, coef=0.97)
        rms_after2 = np.sqrt(np.mean(audio**2))
        print(f"   After preemphasis RMS level: {rms_after2:.4f}")
        
        # Load WhisperX model - using tiny for speed
        print("\n🔄 Loading WhisperX tiny model...")
        start_time = time.time()
        model = whisperx.load_model("tiny", device="cpu", compute_type="int8")
        print(f"✅ Model loaded in {time.time() - start_time:.2f} seconds")
        
        # Transcribe audio
        print("\n🎯 Transcribing audio...")
        start_time = time.time()
        result = model.transcribe(audio, batch_size=4, language="pt")
        print(f"✅ Transcription completed in {time.time() - start_time:.2f} seconds")
        
        # Print transcription result
        print("\n📝 Transcription result:")
        if "text" in result:
            print(result["text"])
        else:
            print(f"Found segments: {len(result.get('segments', []))} segments")
            for i, segment in enumerate(result.get('segments', [])[:3]):
                if i < 3:  # Show first 3 segments
                    print(f"  Segment {i+1}: {segment.get('text', 'No text')}")
            if len(result.get('segments', [])) > 3:
                print(f"  ... and {len(result.get('segments', [])) - 3} more segments")
        
        # Print segments
        print("\n📝 Transcription segments:")
        segments = result.get("segments", [])
        if segments:
            for i, segment in enumerate(segments):
                print(f"Segment {i+1}: {segment.get('start', 0):.2f}s - {segment.get('end', 0):.2f}s: {segment.get('text', 'No text')}")
        else:
            print("No segments found in transcription result")
            
        # Try alignment
        print("\n🔄 Loading alignment model...")
        try:
            start_time = time.time()
            align_model, align_metadata = whisperx.load_align_model(language_code="pt", device="cpu")
            print(f"✅ Alignment model loaded in {time.time() - start_time:.2f} seconds")
            
            print("\n🎯 Running alignment...")
            start_time = time.time()
            aligned_segments = whisperx.align(
                result["segments"], 
                align_model, 
                align_metadata, 
                audio, 
                "cpu",
                return_char_alignments=False
            )
            print(f"✅ Alignment completed in {time.time() - start_time:.2f} seconds")
            
            print("\n📝 Alignment result:")
            print(f"Found {len(aligned_segments.get('segments', []))} aligned segments")
            
            # Show the aligned words in first segment
            if aligned_segments.get("segments") and aligned_segments.get("segments")[0].get("words"):
                print("\nFirst segment word alignments:")
                first_segment = aligned_segments.get("segments")[0]
                for i, word in enumerate(first_segment.get("words", [])[:10]):  # Show first 10 words
                    print(f"  Word {i+1}: {word.get('start', 0):.2f}s - {word.get('end', 0):.2f}s: {word.get('word', 'No word')}")
                
                print("\n🎉 Success! WhisperX alignment is working with PyTorch 2.6+")
            else:
                print("No word alignments found in result")
        except Exception as e:
            print(f"❌ Alignment failed: {e}")
        
        return True
        
    except Exception as e:
        import traceback
        print(f"❌ Error: {str(e)}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)