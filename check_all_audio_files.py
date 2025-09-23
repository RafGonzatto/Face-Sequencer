#!/usr/bin/env python3
"""
Verificar durações de todos os arquivos de áudio para identificar o de 556ms
"""

import librosa
import os
from glob import glob

def check_all_audio_files():
    """Verificar duração de todos os arquivos de áudio"""
    
    print("🔍 Verificando durações de todos os arquivos de áudio...")
    
    # Look for audio files in uploads and root
    audio_patterns = [
        "uploads/audio/*.wav",
        "uploads/audio/*.mp3", 
        "*.mp3",
        "*.wav"
    ]
    
    all_files = []
    for pattern in audio_patterns:
        all_files.extend(glob(pattern))
    
    print(f"📁 Encontrados {len(all_files)} arquivos:")
    
    for audio_file in all_files:
        try:
            if os.path.exists(audio_file):
                audio, sample_rate = librosa.load(audio_file, sr=16000)
                duration = len(audio) / sample_rate
                duration_ms = duration * 1000
                
                print(f"   {os.path.basename(audio_file)}: {duration:.3f}s ({duration_ms:.0f}ms)")
                
                # Check if this might be the problematic file
                if 500 <= duration_ms <= 600:  # Around 556ms
                    print(f"   ⚠️  POSSÍVEL CANDIDATO: {audio_file}")
                    
                    # Test alignment with this file
                    print(f"   🧪 Testando alinhamento com este arquivo...")
                    test_alignment_with_file(audio_file)
            
        except Exception as e:
            print(f"   ❌ Erro ao processar {audio_file}: {e}")

def test_alignment_with_file(audio_file):
    """Testar alinhamento com arquivo específico"""
    
    try:
        from audio_aligner import AudioAligner
        
        aligner = AudioAligner()
        text = "test"  # Simple text
        
        result = aligner.align_audio_to_text_enhanced(
            audio_path=audio_file,
            transcript=text,
            method="auto"
        )
        
        if result and isinstance(result, tuple) and len(result) >= 3:
            alignment_result, timeline, frame_states = result
            
            if frame_states:
                fps = 30.0
                video_duration = len(frame_states) / fps
                video_duration_ms = video_duration * 1000
                
                # Load original audio to get exact duration
                audio, sample_rate = librosa.load(audio_file, sr=16000)
                audio_duration = len(audio) / sample_rate
                audio_duration_ms = audio_duration * 1000
                
                print(f"      Áudio: {audio_duration_ms:.0f}ms")
                print(f"      Vídeo: {video_duration_ms:.0f}ms")
                print(f"      Diferença: {abs(video_duration_ms - audio_duration_ms):.0f}ms")
                
                if abs(video_duration_ms - audio_duration_ms) > 100:  # More than 100ms
                    print(f"      🚨 PROBLEMA ENCONTRADO! Diferença significativa")
                    
                    # Detailed analysis
                    print(f"      📊 Timeline elements: {len(timeline)}")
                    if timeline:
                        timeline_end = max([t.end_time for t in timeline])
                        print(f"      📊 Timeline end: {timeline_end:.3f}s ({timeline_end*1000:.0f}ms)")
                else:
                    print(f"      ✅ Timing OK")
        
    except Exception as e:
        print(f"      ❌ Erro no teste: {e}")

if __name__ == "__main__":
    check_all_audio_files()