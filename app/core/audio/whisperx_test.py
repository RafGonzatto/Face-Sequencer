# whisperx_test.py - Direct test of WhisperX with ElevenLabs audio
import os
import sys
import time
import numpy as np
try:
    import librosa  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    librosa = None
try:
    import pytest  # type: ignore
    if 'PYTEST_CURRENT_TEST' in os.environ and librosa is None:
        pytest.skip("Skipping whisperx_test: librosa not installed", allow_module_level=True)
except Exception:
    pass

from app.core.utils.pytorch_compat import patched_load_context, is_problematic_version, ensure_whisperx_safe_globals

try:
    import whisperx  # type: ignore
except Exception:
    whisperx = None
    if 'PYTEST_CURRENT_TEST' in os.environ:
        try:
            import pytest  # type: ignore
            pytest.skip("Skipping whisperx_test: whisperx not installed", allow_module_level=True)
        except Exception:
            pass

def main():
    if whisperx is None or librosa is None:
        print("Dependencies missing; test skipped.")
        return True
    # File to test
    audio_file = "test_audio.mp3"
    
    if not os.path.exists(audio_file):
        print(f"[X] Error: File {audio_file} not found in current directory")
        return False
    
    print(f"🔍 Testing WhisperX directly with file: {audio_file}")
    print(f"📂 Full path: {os.path.abspath(audio_file)}")
    
    try:
        # Load audio file with librosa
        print("[CHART] Loading audio with librosa...")
        start_time = time.time()
        audio, sample_rate = librosa.load(audio_file, sr=16000, mono=True)
        print(f"[CHECK] Audio loaded in {time.time() - start_time:.2f} seconds")
        print(f"   Sample rate: {sample_rate}, Duration: {len(audio) / sample_rate:.2f} seconds")
        
        # Process audio
        print("[CHART] Processing audio...")
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
        print("\n[REFRESH] Loading WhisperX tiny model...")
        start_time = time.time()
        if is_problematic_version():
            ensure_whisperx_safe_globals()
            with patched_load_context():
                model = whisperx.load_model("tiny", device="cpu", compute_type="int8")
        else:
            model = whisperx.load_model("tiny", device="cpu", compute_type="int8")
        print(f"[CHECK] Model loaded in {time.time() - start_time:.2f} seconds")
        
        # Transcribe audio
        print("\n[TARGET] Transcribing audio...")
        start_time = time.time()
        result = model.transcribe(audio, batch_size=4, language="pt")
        print(f"[CHECK] Transcription completed in {time.time() - start_time:.2f} seconds")
        
        # Print transcription result
        print("\n[NOTE] Transcription result:")
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
        print("\n[NOTE] Transcription segments:")
        segments = result.get("segments", [])
        if segments:
            for i, segment in enumerate(segments):
                print(f"Segment {i+1}: {segment.get('start', 0):.2f}s - {segment.get('end', 0):.2f}s: {segment.get('text', 'No text')}")
        else:
            print("No segments found in transcription result")
            
        # Try alignment
        print("\n[REFRESH] Loading alignment model...")
        try:
            start_time = time.time()
            align_model, align_metadata = whisperx.load_align_model(language_code="pt", device="cpu")
            print(f"[CHECK] Alignment model loaded in {time.time() - start_time:.2f} seconds")
            
            print("\n[TARGET] Running alignment...")
            start_time = time.time()
            aligned_segments = whisperx.align(
                result["segments"], 
                align_model, 
                align_metadata, 
                audio, 
                "cpu",
                return_char_alignments=False
            )
            print(f"[CHECK] Alignment completed in {time.time() - start_time:.2f} seconds")
            
            print("\n[NOTE] Alignment result:")
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
            print(f"[X] Alignment failed: {e}")
        
        return True
        
    except Exception as e:
        import traceback
        print(f"[X] Error: {str(e)}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)