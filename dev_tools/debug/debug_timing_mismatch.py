#!/usr/bin/env python3
"""
Debug de timing - investigar por que vídeo tem 775ms quando áudio tem 556ms
"""

import librosa
import numpy as np
from audio_aligner import AudioAligner
from frame_synchronizer import PreciseFrameSynchronizer

def debug_timing_mismatch():
    """Debug detalhado do problema de timing"""
    
    print("🐛 Debug do problema de timing...")
    
    audio_file = "test_audio.mp3"
    
    # 1. Check actual audio duration
    print(f"\n📊 1. Duração do áudio original:")
    raw_audio, sample_rate = librosa.load(audio_file, sr=16000)
    raw_duration = len(raw_audio) / sample_rate
    print(f"   Áudio RAW: {raw_duration:.3f}s ({len(raw_audio)} samples)")
    
    # 2. Check processed audio duration
    print(f"\n🔧 2. Duração após processamento:")
    aligner = AudioAligner()
    processed_audio, sr = aligner.preprocess_audio(audio_file)
    processed_duration = len(processed_audio) / sr
    print(f"   Áudio processado: {processed_duration:.3f}s ({len(processed_audio)} samples)")
    
    # 3. Run alignment and check timeline
    print(f"\n🎯 3. Executando alinhamento...")
    
    # Simple text for testing
    text = "Hello world test"
    
    try:
        result = aligner.align_audio_to_text_enhanced(
            audio_path=audio_file,
            transcript=text,
            method="auto"  # Use "auto" instead of "transformers"
        )
        
        if result and isinstance(result, tuple) and len(result) >= 3:
            alignment_result, timeline, frame_states = result
            
            print(f"\n📋 4. Análise da timeline:")
            print(f"   Elementos da timeline: {len(timeline)}")
            
            if timeline:
                # Find actual timeline duration
                timeline_start = min([t.start_time for t in timeline])
                timeline_end = max([t.end_time for t in timeline])
                timeline_duration = timeline_end - timeline_start
                
                print(f"   Timeline start: {timeline_start:.3f}s")
                print(f"   Timeline end: {timeline_end:.3f}s")
                print(f"   Timeline duration: {timeline_duration:.3f}s")
                
                # Check individual segments
                total_word_duration = 0
                total_pause_duration = 0
                
                print(f"\n📝 5. Detalhes dos segmentos:")
                for i, element in enumerate(timeline[:10]):  # First 10 elements
                    if element.word == 'PAUSE':
                        total_pause_duration += element.duration
                        segment_type = "PAUSE"
                    else:
                        total_word_duration += element.duration
                        segment_type = "WORD"
                    
                    print(f"   {i+1:2d}. {segment_type:5s} {element.word[:10]:10s} "
                          f"{element.start_time:6.3f}s - {element.end_time:6.3f}s "
                          f"({element.duration:5.3f}s)")
                
                print(f"\n📊 6. Resumo das durações:")
                print(f"   Total word duration: {total_word_duration:.3f}s")
                print(f"   Total pause duration: {total_pause_duration:.3f}s")
                print(f"   Sum of all segments: {total_word_duration + total_pause_duration:.3f}s")
            
            # 7. Check frame generation
            print(f"\n🎬 7. Análise da geração de frames:")
            
            if frame_states:
                fps = 30.0  # Default FPS
                video_duration = len(frame_states) / fps
                
                print(f"   Total frames: {len(frame_states)}")
                print(f"   FPS: {fps}")
                print(f"   Video duration: {video_duration:.3f}s")
                print(f"   Audio duration: {processed_duration:.3f}s")
                print(f"   Difference: {abs(video_duration - processed_duration):.3f}s")
                
                if abs(video_duration - processed_duration) > 0.1:  # More than 100ms difference
                    print(f"   ❌ PROBLEMA: Diferença significativa de timing!")
                    
                    # Check frame timing
                    print(f"\n🔍 8. Análise dos frames:")
                    frame_times = [state.timestamp for state in frame_states]
                    
                    if frame_times:
                        print(f"   Primeiro frame: {frame_times[0]:.3f}s")
                        print(f"   Último frame: {frame_times[-1]:.3f}s")
                        print(f"   Span dos frames: {frame_times[-1] - frame_times[0]:.3f}s")
                        
                        # Check for gaps or overlaps
                        time_diffs = np.diff(frame_times)
                        expected_frame_time = 1.0 / fps
                        
                        print(f"   Tempo esperado entre frames: {expected_frame_time:.6f}s")
                        print(f"   Tempo médio entre frames: {np.mean(time_diffs):.6f}s")
                        print(f"   Min tempo entre frames: {np.min(time_diffs):.6f}s")
                        print(f"   Max tempo entre frames: {np.max(time_diffs):.6f}s")
                        
                        # Find problematic frame transitions
                        large_gaps = np.where(time_diffs > expected_frame_time * 1.5)[0]
                        if len(large_gaps) > 0:
                            print(f"   ⚠️  {len(large_gaps)} gaps grandes encontrados:")
                            for gap_idx in large_gaps[:5]:  # Show first 5
                                print(f"      Frame {gap_idx}: {time_diffs[gap_idx]:.6f}s gap")
                
                else:
                    print(f"   ✅ Timing parece correto")
        
        else:
            print("❌ Falha no alinhamento")
            return False
        
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    debug_timing_mismatch()