# test_audio.py - Simplified test for audio processing
import os
import sys
import time
import wave
import contextlib
from pydub import AudioSegment
import numpy as np

def main():
    # File to test
    audio_file = "ElevenLabs_2025-09-22T18_53_43_Ethan_pre_sp100_s50_sb75_se0_b_m2.mp3"
    
    if not os.path.exists(audio_file):
        print(f"❌ Error: File {audio_file} not found in current directory")
        return False
    
    print(f"🔍 Testing audio processing with file: {audio_file}")
    print(f"📂 Full path: {os.path.abspath(audio_file)}")
    
    try:
        # Convert to WAV for easier processing
        print("🔄 Converting MP3 to WAV...")
        start_time = time.time()
        
        audio = AudioSegment.from_file(audio_file)
        temp_wav = "temp_audio.wav"
        audio.export(temp_wav, format="wav")
        
        print(f"✅ Conversion completed in {time.time() - start_time:.2f} seconds")
        
        # Get basic audio properties
        with contextlib.closing(wave.open(temp_wav, 'r')) as f:
            frames = f.getnframes()
            rate = f.getframerate()
            duration = frames / float(rate)
            channels = f.getnchannels()
        
        print(f"📊 Audio Properties:")
        print(f"   - Duration: {duration:.2f} seconds")
        print(f"   - Sample Rate: {rate} Hz")
        print(f"   - Channels: {channels}")
        print(f"   - Frames: {frames}")
        
        # Basic speech detection check
        print("🔍 Checking for speech content...")
        start_time = time.time()
        
        # Convert to numpy array
        samples = np.array(audio.get_array_of_samples())
        if audio.channels == 2:
            # Convert stereo to mono by averaging channels
            samples = samples.reshape((-1, 2)).mean(axis=1)
        
        # Calculate RMS energy
        rms = np.sqrt(np.mean(samples**2))
        
        # Simple threshold-based speech detection
        if rms > 500:  # Arbitrary threshold
            print(f"✅ Speech detected! RMS energy: {rms:.2f}")
        else:
            print(f"⚠️ Low audio levels detected. RMS energy: {rms:.2f}")
        
        print(f"✅ Analysis completed in {time.time() - start_time:.2f} seconds")
        
        # Clean up
        if os.path.exists(temp_wav):
            os.remove(temp_wav)
            print("🧹 Removed temporary WAV file")
        
        print("\n✅ Test completed successfully!")
        return True
        
    except Exception as e:
        import traceback
        print(f"❌ Error: {str(e)}")
        traceback.print_exc()
        
        # Clean up on error
        if 'temp_wav' in locals() and os.path.exists(temp_wav):
            os.remove(temp_wav)
        
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)