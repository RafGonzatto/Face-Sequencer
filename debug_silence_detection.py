#!/usr/bin/env python3
"""
Debug script to test silence detection on the user's audio
"""

import librosa
import numpy as np
from enhanced_silence_detector import EnhancedSilenceDetector
import os

def test_silence_detection_on_user_audio():
    """Test silence detection on the actual audio file being used"""
    
    print("🧪 Testando detecção de silêncio no áudio do usuário...")
    
    # Find the ElevenLabs audio file
    audio_file = "test_audio.mp3"
    
    if not os.path.exists(audio_file):
        print(f"❌ Arquivo de áudio não encontrado: {audio_file}")
        return False
    
    print(f"📁 Carregando áudio: {audio_file}")
    
    # Load audio
    try:
        audio, sample_rate = librosa.load(audio_file, sr=16000)
        duration = len(audio) / sample_rate
        print(f"🎵 Áudio carregado: {duration:.2f}s, {len(audio)} amostras, {sample_rate}Hz")
    except Exception as e:
        print(f"❌ Erro ao carregar áudio: {e}")
        return False
    
    # Create silence detector
    detector = EnhancedSilenceDetector(sample_rate=sample_rate)
    
    # Try different threshold sensitivities
    print(f"\n🔍 Testando diferentes sensibilidades...")
    
    sensitivities = [
        {"name": "Padrão", "min_silence": 0.1, "energy_factor": 1.0},
        {"name": "Mais Sensível", "min_silence": 0.05, "energy_factor": 0.5},
        {"name": "Muito Sensível", "min_silence": 0.03, "energy_factor": 0.3},
        {"name": "Ultra Sensível", "min_silence": 0.02, "energy_factor": 0.1}
    ]
    
    for sens in sensitivities:
        print(f"\n🎯 Teste: {sens['name']}")
        print(f"   Silêncio mínimo: {sens['min_silence']}s")
        print(f"   Fator energia: {sens['energy_factor']}")
        
        # Adjust detector parameters
        detector.min_silence_duration = sens['min_silence']
        
        # Calculate energy manually with adjusted threshold
        frames = detector._frame_audio(audio)
        energy = np.array([np.sqrt(np.mean(frame**2)) for frame in frames])
        
        # Compute adaptive threshold with factor
        energy_15th = np.percentile(energy, 15)
        energy_75th = np.percentile(energy, 75)
        adjusted_threshold = energy_15th + (energy_75th - energy_15th) * 0.25 * sens['energy_factor']
        
        print(f"   Threshold energia ajustado: {adjusted_threshold:.6f}")
        
        # Detect silences with manual threshold
        silence_segments = detector.detect_silence_segments(
            audio, 
            energy_threshold=adjusted_threshold,
            adaptive_thresholds=False
        )
        
        print(f"   🎯 Detectados: {len(silence_segments)} segmentos")
        
        if silence_segments:
            total_silence = sum(seg.duration for seg in silence_segments)
            print(f"   ⏱️ Total silêncio: {total_silence:.2f}s ({total_silence/duration*100:.1f}%)")
            
            print(f"   📋 Primeiros 5 segmentos:")
            for i, seg in enumerate(silence_segments[:5]):
                print(f"      {i+1}. {seg.start_time:.2f}s - {seg.end_time:.2f}s ({seg.duration:.3f}s)")
        else:
            print(f"   ❌ Nenhum silêncio detectado")
    
    # Test with very permissive settings
    print(f"\n🚨 Teste EXTREMAMENTE sensível:")
    detector.min_silence_duration = 0.01  # 10ms minimum
    
    # Manual very low threshold
    energy = np.array([np.sqrt(np.mean(frame**2)) for frame in detector._frame_audio(audio)])
    very_low_threshold = np.min(energy[energy > 0]) * 2  # 2x minimum non-zero energy
    
    print(f"   Threshold ultra-baixo: {very_low_threshold:.8f}")
    
    ultra_segments = detector.detect_silence_segments(
        audio,
        energy_threshold=very_low_threshold,
        adaptive_thresholds=False
    )
    
    print(f"   🎯 Segmentos ultra-sensível: {len(ultra_segments)}")
    
    if ultra_segments:
        total_ultra = sum(seg.duration for seg in ultra_segments)
        print(f"   ⏱️ Total ultra silêncio: {total_ultra:.2f}s ({total_ultra/duration*100:.1f}%)")
        
        # Show where gaps are
        print(f"   📋 Todos os gaps detectados:")
        for i, seg in enumerate(ultra_segments):
            print(f"      {i+1:2d}. {seg.start_time:5.2f}s - {seg.end_time:5.2f}s ({seg.duration:6.3f}s)")
    
    # Visualize energy to understand audio characteristics
    print(f"\n📊 Análise de energia do áudio:")
    min_energy = np.min(energy)
    max_energy = np.max(energy)
    mean_energy = np.mean(energy)
    std_energy = np.std(energy)
    
    print(f"   Energia mín: {min_energy:.6f}")
    print(f"   Energia máx: {max_energy:.6f}")  
    print(f"   Energia média: {mean_energy:.6f}")
    print(f"   Desvio padrão: {std_energy:.6f}")
    print(f"   Percentil 15: {np.percentile(energy, 15):.6f}")
    print(f"   Percentil 25: {np.percentile(energy, 25):.6f}")
    print(f"   Percentil 50: {np.percentile(energy, 50):.6f}")
    
    return len(ultra_segments) > 0

if __name__ == "__main__":
    success = test_silence_detection_on_user_audio()
    
    if success:
        print(f"\n✅ Detecção funcionando - encontrou silêncios no áudio")
    else:
        print(f"\n❌ Problema na detecção - não encontrou silêncios suficientes")