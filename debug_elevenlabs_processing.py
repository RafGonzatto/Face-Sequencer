#!/usr/bin/env python3
"""
Debug específico do processamento de áudio ElevenLabs para ver por que a detecção falha
"""

import librosa
import numpy as np
from enhanced_silence_detector import EnhancedSilenceDetector
from audio_aligner import AudioAligner

def debug_elevenlabs_processing():
    """Debug do processamento ElevenLabs específico"""
    
    print("🔬 Debug específico do processamento ElevenLabs...")
    
    audio_file = "test_audio.mp3"
    
    # 1. Load audio RAW (como no debug anterior)
    print(f"\n📁 1. Áudio RAW (sem processamento):")
    raw_audio, sample_rate = librosa.load(audio_file, sr=16000)
    print(f"   Duração: {len(raw_audio)/sample_rate:.2f}s")
    print(f"   RMS: {np.sqrt(np.mean(raw_audio**2)):.6f}")
    
    # Test silence detection on raw audio
    detector = EnhancedSilenceDetector(sample_rate=sample_rate)
    raw_segments = detector.detect_silence_segments(raw_audio, adaptive_thresholds=True)
    print(f"   Silêncios detectados: {len(raw_segments)}")
    
    # 2. Process audio like AudioAligner does
    print(f"\n🔧 2. Áudio processado (como AudioAligner):")
    aligner = AudioAligner()
    processed_audio, sr = aligner.preprocess_audio(audio_file)
    print(f"   Duração: {len(processed_audio)/sr:.2f}s")
    print(f"   RMS: {np.sqrt(np.mean(processed_audio**2)):.6f}")
    
    # Test silence detection on processed audio
    processed_segments = detector.detect_silence_segments(processed_audio, adaptive_thresholds=True)
    print(f"   Silêncios detectados: {len(processed_segments)}")
    
    # 3. Compare energies
    print(f"\n📊 3. Comparação de energia:")
    
    # Raw audio energy
    raw_frames = detector._frame_audio(raw_audio)
    raw_energy = np.array([np.sqrt(np.mean(frame**2)) for frame in raw_frames])
    
    # Processed audio energy  
    proc_frames = detector._frame_audio(processed_audio)
    proc_energy = np.array([np.sqrt(np.mean(frame**2)) for frame in proc_frames])
    
    print(f"   RAW - Frames: {len(raw_energy)}, Energy range: {np.min(raw_energy):.6f} - {np.max(raw_energy):.6f}")
    print(f"   PROC - Frames: {len(proc_energy)}, Energy range: {np.min(proc_energy):.6f} - {np.max(proc_energy):.6f}")
    
    # 4. Check thresholds used
    print(f"\n🎯 4. Thresholds:")
    
    # Raw thresholds
    raw_15th = np.percentile(raw_energy, 15)
    raw_75th = np.percentile(raw_energy, 75)
    raw_threshold = raw_15th + (raw_75th - raw_15th) * 0.25
    
    # Processed thresholds
    proc_15th = np.percentile(proc_energy, 15)
    proc_75th = np.percentile(proc_energy, 75)
    proc_threshold = proc_15th + (proc_75th - proc_15th) * 0.25
    
    print(f"   RAW threshold: {raw_threshold:.6f} (15th: {raw_15th:.6f}, 75th: {raw_75th:.6f})")
    print(f"   PROC threshold: {proc_threshold:.6f} (15th: {proc_15th:.6f}, 75th: {proc_75th:.6f})")
    
    # 5. Manual silence detection with very low thresholds
    print(f"\n🚨 5. Forçando detecção com threshold baixo:")
    
    # Try with 1% of median energy
    median_energy = np.median(proc_energy)
    forced_threshold = median_energy * 0.01
    
    print(f"   Mediana energia: {median_energy:.6f}")
    print(f"   Threshold forçado: {forced_threshold:.6f}")
    
    forced_segments = detector.detect_silence_segments(
        processed_audio,
        energy_threshold=forced_threshold,
        adaptive_thresholds=False
    )
    
    print(f"   Silêncios forçados: {len(forced_segments)}")
    
    if len(forced_segments) > 0:
        print(f"   Primeiros 5 segmentos:")
        for i, seg in enumerate(forced_segments[:5]):
            print(f"      {i+1}. {seg.start_time:.2f}s - {seg.end_time:.2f}s ({seg.duration:.3f}s)")
    
    # 6. Check if the issue is in the ZCR logic
    print(f"\n🔊 6. Análise ZCR (Zero Crossing Rate):")
    
    zcr = detector._calculate_zcr(processed_audio)
    zcr_threshold = detector._compute_adaptive_zcr_threshold(zcr)
    
    print(f"   ZCR range: {np.min(zcr):.6f} - {np.max(zcr):.6f}")
    print(f"   ZCR threshold: {zcr_threshold:.6f}")
    print(f"   Frames below ZCR threshold: {np.sum(zcr < zcr_threshold)}/{len(zcr)}")
    
    # Test with energy OR zcr logic (like the old version)
    low_energy = proc_energy < proc_threshold
    low_zcr = zcr < zcr_threshold
    
    print(f"\n🧠 7. Lógica de decisão:")
    print(f"   Frames baixa energia: {np.sum(low_energy)}/{len(proc_energy)}")
    print(f"   Frames baixo ZCR: {np.sum(low_zcr)}/{len(zcr)}")
    print(f"   Frames ENERGY AND ZCR: {np.sum(low_energy & low_zcr)}")
    print(f"   Frames ENERGY OR ZCR: {np.sum(low_energy | low_zcr)}")
    
    # The problem might be that we need BOTH low energy AND low ZCR
    # But in speech, low energy periods might still have high ZCR due to noise
    
    return len(forced_segments) > 0

if __name__ == "__main__":
    debug_elevenlabs_processing()