#!/usr/bin/env python3
"""
Debug detalhado da energia do áudio para entender por que tudo está sendo detectado como silêncio
"""

import librosa
import numpy as np
from enhanced_silence_detector import EnhancedSilenceDetector
import matplotlib.pyplot as plt

def debug_audio_energy():
    """Análise detalhada da energia do áudio"""
    
    print("🔬 Debug detalhado da energia do áudio...")
    
    # Load audio
    audio_file = "test_audio.mp3"
    audio, sample_rate = librosa.load(audio_file, sr=16000)
    
    print(f"📊 Audio stats:")
    print(f"   Samples: {len(audio)}")
    print(f"   Duration: {len(audio)/sample_rate:.2f}s")
    print(f"   Min amplitude: {np.min(audio):.6f}")
    print(f"   Max amplitude: {np.max(audio):.6f}")
    print(f"   RMS overall: {np.sqrt(np.mean(audio**2)):.6f}")
    
    # Manual frame processing
    detector = EnhancedSilenceDetector(sample_rate=sample_rate)
    frames = detector._frame_audio(audio)
    
    print(f"\n📊 Frame analysis:")
    print(f"   Total frames: {len(frames)}")
    print(f"   Frame length: {detector.frame_length} samples")
    print(f"   Frame shift: {detector.frame_shift} samples")
    
    # Calculate energy manually
    energies = []
    non_zero_count = 0
    
    for i, frame in enumerate(frames[:10]):  # First 10 frames
        rms_energy = np.sqrt(np.mean(frame**2))
        energies.append(rms_energy)
        
        if rms_energy > 0:
            non_zero_count += 1
            
        print(f"   Frame {i:2d}: RMS={rms_energy:.8f}, Max={np.max(np.abs(frame)):.6f}, Mean={np.mean(np.abs(frame)):.6f}")
    
    print(f"   Non-zero frames in sample: {non_zero_count}/10")
    
    # Full energy calculation
    all_energy = np.array([np.sqrt(np.mean(frame**2)) for frame in frames])
    
    print(f"\n📈 Energy distribution:")
    print(f"   Total frames: {len(all_energy)}")
    print(f"   Zero energy frames: {np.sum(all_energy == 0)}")
    print(f"   Non-zero frames: {np.sum(all_energy > 0)}")
    print(f"   Min energy (>0): {np.min(all_energy[all_energy > 0]):.8f}")
    print(f"   Max energy: {np.max(all_energy):.8f}")
    print(f"   Mean energy: {np.mean(all_energy):.8f}")
    
    # Check if audio is actually silent
    print(f"\n🎵 Audio content check:")
    
    # Look at different parts of audio
    total_samples = len(audio)
    segment_size = total_samples // 10
    
    for i in range(10):
        start_idx = i * segment_size
        end_idx = start_idx + segment_size
        segment = audio[start_idx:end_idx]
        
        segment_rms = np.sqrt(np.mean(segment**2))
        segment_max = np.max(np.abs(segment))
        
        print(f"   Segment {i:2d} ({start_idx//sample_rate:2d}s-{end_idx//sample_rate:2d}s): RMS={segment_rms:.6f}, Max={segment_max:.6f}")
    
    # Check if there's actual variation in the audio
    print(f"\n🔍 Audio variation analysis:")
    
    # Calculate moving average to see if there are speech periods
    window_size = sample_rate // 10  # 100ms windows
    moving_rms = []
    
    for i in range(0, len(audio) - window_size, window_size):
        window = audio[i:i + window_size]
        window_rms = np.sqrt(np.mean(window**2))
        moving_rms.append(window_rms)
    
    moving_rms = np.array(moving_rms)
    
    print(f"   Moving RMS windows: {len(moving_rms)}")
    print(f"   Min moving RMS: {np.min(moving_rms):.6f}")
    print(f"   Max moving RMS: {np.max(moving_rms):.6f}")
    print(f"   Mean moving RMS: {np.mean(moving_rms):.6f}")
    print(f"   Std moving RMS: {np.std(moving_rms):.6f}")
    
    # Find the loudest and quietest periods
    loudest_idx = np.argmax(moving_rms)
    quietest_idx = np.argmin(moving_rms)
    
    print(f"\n🔊 Loudest period: {loudest_idx*0.1:.1f}s - RMS: {moving_rms[loudest_idx]:.6f}")
    print(f"🔇 Quietest period: {quietest_idx*0.1:.1f}s - RMS: {moving_rms[quietest_idx]:.6f}")
    
    # Test threshold calculation
    print(f"\n🎯 Threshold analysis:")
    
    # Using different percentiles
    for percentile in [5, 10, 15, 20, 25, 50]:
        threshold = np.percentile(all_energy, percentile)
        below_threshold = np.sum(all_energy < threshold)
        percentage = (below_threshold / len(all_energy)) * 100
        
        print(f"   {percentile:2d}th percentile: {threshold:.6f} -> {below_threshold:4d} frames ({percentage:5.1f}%) below")
    
    # Check the actual decision logic
    print(f"\n🧠 Decision logic analysis:")
    
    # Try the actual threshold from the detector
    energy_15th = np.percentile(all_energy, 15)
    energy_75th = np.percentile(all_energy, 75)
    actual_threshold = energy_15th + (energy_75th - energy_15th) * 0.25
    
    print(f"   15th percentile: {energy_15th:.6f}")
    print(f"   75th percentile: {energy_75th:.6f}")
    print(f"   Actual threshold: {actual_threshold:.6f}")
    
    below_actual = np.sum(all_energy < actual_threshold)
    print(f"   Frames below actual threshold: {below_actual}/{len(all_energy)} ({below_actual/len(all_energy)*100:.1f}%)")
    
    # This should tell us why everything is being classified as silence
    
if __name__ == "__main__":
    debug_audio_energy()