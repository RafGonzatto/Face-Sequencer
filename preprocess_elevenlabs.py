import os
import librosa
import soundfile as sf
import numpy as np
from scipy import signal

def preprocess_elevenlabs_audio():
    print('Loading ElevenLabs audio...')
    input_file = 'ElevenLabs_2025-09-22T18_53_43_Ethan_pre_sp100_s50_sb75_se0_b_m2.mp3'
    output_file = 'uploads/audio/optimized_elevenlabs.wav'

    # Load the audio file
    audio, sr = librosa.load(input_file, sr=None)

    # Calculate RMS before processing
    rms_before = np.sqrt(np.mean(audio**2))
    print(f'RMS before processing: {rms_before:.4f}')

    # Apply preprocessing steps
    # 1. Normalize audio
    normalized_audio = librosa.util.normalize(audio)

    # 2. High-pass filter to remove very low frequencies
    cutoff = 80  # Hz
    nyquist = sr / 2
    normal_cutoff = cutoff / nyquist
    b, a = signal.butter(4, normal_cutoff, btype='high', analog=False)
    filtered_audio = signal.filtfilt(b, a, normalized_audio)

    # 3. Apply pre-emphasis filter
    pre_emphasis = 0.97
    emphasized_audio = np.append(filtered_audio[0], filtered_audio[1:] - pre_emphasis * filtered_audio[:-1])

    # 4. Trim silence
    trimmed_audio, _ = librosa.effects.trim(emphasized_audio, top_db=30)

    # 5. Final normalization to ensure good volume
    final_audio = librosa.util.normalize(trimmed_audio)

    # Calculate RMS after processing
    rms_after = np.sqrt(np.mean(final_audio**2))
    print(f'RMS after processing: {rms_after:.4f}')

    # Save the preprocessed audio
    print(f'Saving optimized audio to {output_file}')
    sf.write(output_file, final_audio, sr)
    print('Pre-processing complete!')

if __name__ == "__main__":
    preprocess_elevenlabs_audio()