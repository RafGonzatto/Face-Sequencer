# process_elevenlabs.py - Pre-process the ElevenLabs audio file
import os
import librosa
import soundfile as sf
import numpy as np
from scipy.signal import butter, filtfilt
import shutil

def main():
    # Source audio file
    source_file = "test_audio.mp3"
    
    if not os.path.exists(source_file):
        print(f"❌ Error: File {source_file} not found")
        return False
    
    print(f"🔍 Pre-processing ElevenLabs audio file: {source_file}")
    
    # Destination folder
    dest_folder = "uploads/audio"
    os.makedirs(dest_folder, exist_ok=True)
    
    # Generate optimized file name
    dest_file = os.path.join(dest_folder, "optimized_elevenlabs.wav")
    
    try:
        # Load audio
        print("📊 Loading audio...")
        audio, sr = librosa.load(source_file, sr=16000, mono=True)
        
        # Print original stats
        rms = np.sqrt(np.mean(audio**2))
        print(f"Original RMS: {rms:.4f}, Duration: {len(audio)/sr:.2f}s")
        
        # Apply processing chain
        print("🔄 Processing audio...")
        
        # 1. Normalize (increase volume)
        audio = librosa.util.normalize(audio) * 0.95
        
        # 2. High-pass filter (remove rumble)
        nyq = 0.5 * sr
        cutoff = 100 / nyq  # 100Hz high-pass
        b, a = butter(3, cutoff, btype='high')
        audio = filtfilt(b, a, audio)
        
        # 3. Pre-emphasis (enhance speech)
        audio = librosa.effects.preemphasis(audio, coef=0.97)
        
        # 4. Trim silence
        audio, _ = librosa.effects.trim(audio, top_db=15)
        
        # Save processed file
        print(f"💾 Saving processed file to {dest_file}")
        sf.write(dest_file, audio, sr, subtype='PCM_16')
        
        # Also copy original to uploads folder for comparison
        orig_copy = os.path.join(dest_folder, "original_elevenlabs.mp3")
        shutil.copy2(source_file, orig_copy)
        
        print(f"✅ Processing complete. Files saved to uploads/audio folder")
        
        # Print new stats
        rms_new = np.sqrt(np.mean(audio**2))
        print(f"New RMS: {rms_new:.4f}, Duration: {len(audio)/sr:.2f}s")
        
        return True
    
    except Exception as e:
        try:
            # Try to use centralized logging
            from logger import get_logger, log_exception
            audio_logger = get_logger('audio.elevenlabs')
            log_exception(audio_logger, e, {'phase': 'processing'})
        except ImportError:
            # Fall back to basic logging if logger module isn't available
            import traceback
            print(f"❌ Error: {str(e)}")
            traceback.print_exc()
        return False

if __name__ == "__main__":
    main()