#!/usr/bin/env python
# enhanced_elevenlabs_processor.py - Comprehensive ElevenLabs Audio Optimizer
import os
import librosa
import soundfile as sf
import numpy as np
from scipy import signal
import shutil
import matplotlib.pyplot as plt
import time
from pathlib import Path
import argparse

def process_elevenlabs_audio(input_file=None, output_file=None, plot=False, verbose=True):
    """
    Enhanced processing for ElevenLabs audio files to optimize for speech animation alignment.
    
    Args:
        input_file: Path to the input audio file (default: looks for ElevenLabs file in current dir)
        output_file: Path to save the optimized audio file (default: uploads/audio/optimized_elevenlabs.wav)
        plot: Whether to generate and save visualizations of the audio processing
        verbose: Whether to print detailed information about the processing
        
    Returns:
        bool: True if processing succeeded, False otherwise
    """
    # Default input file pattern if none provided
    if input_file is None:
        # Look for ElevenLabs files in current directory
        elevenlabs_files = list(Path('.').glob('ElevenLabs*.mp3'))
        if not elevenlabs_files:
            if verbose:
                print("❌ Error: No ElevenLabs audio files found in the current directory")
            return False
        
        # Use the most recent file if multiple exist
        input_file = str(sorted(elevenlabs_files, key=lambda p: p.stat().st_mtime, reverse=True)[0])
        
    if output_file is None:
        output_dir = "uploads/audio"
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, "optimized_elevenlabs.wav")
    
    if verbose:
        print(f"🔍 Processing ElevenLabs audio file: {input_file}")
        print(f"📁 Output will be saved to: {output_file}")
    
    try:
        # Load audio with original sample rate
        if verbose:
            print("📊 Loading audio...")
        
        # First load to get original sample rate
        audio, original_sr = librosa.load(input_file, sr=None)
        
        # Then reload at 16kHz (optimal for speech processing)
        audio, sr = librosa.load(input_file, sr=16000)
        
        # Print original stats
        duration = len(audio) / sr
        rms = np.sqrt(np.mean(audio**2))
        peak = np.max(np.abs(audio))
        
        if verbose:
            print(f"Original stats:")
            print(f"- Sample rate: {original_sr} Hz (processing at {sr} Hz)")
            print(f"- Duration: {duration:.2f} seconds")
            print(f"- RMS level: {rms:.4f}")
            print(f"- Peak level: {peak:.4f}")
        
        # Save original waveform for comparison if plotting enabled
        if plot:
            original_audio = audio.copy()
        
        # Apply audio enhancement pipeline
        if verbose:
            print("🔧 Enhancing audio quality...")
        
        # Step 1: High-pass filter to remove low rumble (below 80Hz)
        if verbose:
            print("  - Applying high-pass filter (80Hz cutoff)...")
        
        nyquist = sr / 2
        cutoff = 80 / nyquist
        b, a = signal.butter(4, cutoff, btype='high', analog=False)
        audio = signal.filtfilt(b, a, audio)
        
        # Step 2: Apply slight compression to even out levels
        if verbose:
            print("  - Applying dynamic range compression...")
            
        # Simple compression implementation
        threshold = 0.15
        ratio = 3.0
        makeup_gain = 1.5
        
        # Calculate gain reduction
        gain_mask = np.abs(audio) > threshold
        gain_reduction = np.ones_like(audio)
        gain_reduction[gain_mask] = 1.0 + (ratio - 1.0) * (np.abs(audio[gain_mask]) - threshold) / (1.0 - threshold)
        
        # Apply compression with makeup gain
        audio = audio / gain_reduction * makeup_gain
        
        # Step 3: Pre-emphasis to enhance speech clarity
        if verbose:
            print("  - Applying pre-emphasis filter...")
            
        pre_emphasis = 0.97
        audio = np.append(audio[0], audio[1:] - pre_emphasis * audio[:-1])
        
        # Step 4: Trim silence at beginning and end
        if verbose:
            print("  - Trimming silence...")
            
        audio, _ = librosa.effects.trim(audio, top_db=20)
        
        # Step 5: Final normalization
        if verbose:
            print("  - Normalizing audio levels...")
            
        audio = librosa.util.normalize(audio) * 0.95  # Slight headroom
        
        # Calculate final stats
        new_duration = len(audio) / sr
        new_rms = np.sqrt(np.mean(audio**2))
        new_peak = np.max(np.abs(audio))
        
        if verbose:
            print(f"Enhanced stats:")
            print(f"- Duration: {new_duration:.2f} seconds ({duration - new_duration:.2f}s shorter)")
            print(f"- RMS level: {new_rms:.4f} ({(new_rms/rms - 1)*100:.1f}% change)")
            print(f"- Peak level: {new_peak:.4f}")
        
        # Save processed audio file
        if verbose:
            print(f"💾 Saving enhanced audio to {output_file}")
        
        sf.write(output_file, audio, sr, subtype='PCM_16')
        
        # Also copy original to uploads folder for comparison
        original_copy = os.path.join(os.path.dirname(output_file), "original_elevenlabs.mp3")
        shutil.copy2(input_file, original_copy)
        
        # Generate comparison plots if requested
        if plot:
            plot_filename = os.path.join(os.path.dirname(output_file), "audio_enhancement.png")
            if verbose:
                print(f"📊 Generating audio comparison plot: {plot_filename}")
            
            plt.figure(figsize=(12, 8))
            
            # Time domain plots
            plt.subplot(2, 2, 1)
            plt.title("Original Waveform")
            plt.plot(np.linspace(0, duration, len(original_audio)), original_audio)
            plt.xlabel("Time (s)")
            plt.grid(True, alpha=0.3)
            
            plt.subplot(2, 2, 2)
            plt.title("Enhanced Waveform")
            plt.plot(np.linspace(0, new_duration, len(audio)), audio)
            plt.xlabel("Time (s)")
            plt.grid(True, alpha=0.3)
            
            # Frequency domain plots
            plt.subplot(2, 2, 3)
            S_original = librosa.amplitude_to_db(np.abs(librosa.stft(original_audio)), ref=np.max)
            librosa.display.specshow(S_original, y_axis='log', x_axis='time', sr=sr)
            plt.colorbar(format='%+2.0f dB')
            plt.title('Original Spectrogram')
            
            plt.subplot(2, 2, 4)
            S_enhanced = librosa.amplitude_to_db(np.abs(librosa.stft(audio)), ref=np.max)
            librosa.display.specshow(S_enhanced, y_axis='log', x_axis='time', sr=sr)
            plt.colorbar(format='%+2.0f dB')
            plt.title('Enhanced Spectrogram')
            
            plt.tight_layout()
            plt.savefig(plot_filename)
            
            if verbose:
                print(f"📊 Plot saved to {plot_filename}")
        
        if verbose:
            print("✅ Audio enhancement complete!")
        
        return True
        
    except Exception as e:
        import traceback
        print(f"❌ Error during audio processing: {str(e)}")
        traceback.print_exc()
        return False

def main():
    """Command-line interface for the enhanced audio processor"""
    parser = argparse.ArgumentParser(
        description="Enhanced ElevenLabs Audio Processor for better lip sync alignment"
    )
    parser.add_argument("--input", "-i", help="Path to the input audio file")
    parser.add_argument("--output", "-o", help="Path to save the optimized audio file")
    parser.add_argument("--plot", "-p", action="store_true", help="Generate visualization plots")
    parser.add_argument("--quiet", "-q", action="store_true", help="Run without detailed output")
    args = parser.parse_args()
    
    success = process_elevenlabs_audio(
        input_file=args.input,
        output_file=args.output,
        plot=args.plot,
        verbose=not args.quiet
    )
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())