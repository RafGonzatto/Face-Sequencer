#!/usr/bin/env python3
"""
Debug específico para encontrar a fonte dos valores 556ms e 775ms
"""

import librosa
import numpy as np
from audio_aligner import AudioAligner
import os

def debug_specific_measurements():
    """Debug focado nos valores específicos mencionados pelo usuário"""
    
    print("🔍 Debug específico para valores 556ms e 775ms...")
    
    # Test with the main ElevenLabs file
    audio_file = "test_audio.mp3"
    
    if not os.path.exists(audio_file):
        print(f"❌ Arquivo principal não encontrado: {audio_file}")
        return False
    
    # 1. Check if there are segments or clips with these durations
    print(f"\n1. 📊 Analisando segmentos e possíveis clips...")
    
    # Load and analyze audio
    audio, sample_rate = librosa.load(audio_file, sr=16000)
    duration = len(audio) / sample_rate
    
    print(f"   Áudio completo: {duration:.3f}s ({duration*1000:.0f}ms)")
    
    # Look for segments around 556ms in the audio
    target_duration_ms = 556
    target_duration_s = target_duration_ms / 1000
    tolerance = 0.05  # 50ms tolerance
    
    print(f"\n2. 🎯 Procurando segmentos de ~{target_duration_ms}ms...")
    
    # Check different segment sizes
    segment_sizes = [0.5, 1.0, 2.0, 3.0, 5.0, 10.0]  # seconds
    
    for segment_size in segment_sizes:
        if segment_size < duration:
            segment_samples = int(segment_size * sample_rate)
            
            # Check energy in this segment
            segment = audio[:segment_samples]
            segment_rms = np.sqrt(np.mean(segment**2))
            
            print(f"   Segmento {segment_size}s: {segment_size*1000:.0f}ms, RMS: {segment_rms:.6f}")
            
            if abs(segment_size*1000 - target_duration_ms) < tolerance*1000:
                print(f"      ⭐ MATCH! Este segmento tem duração próxima a {target_duration_ms}ms")
    
    # 3. Test alignment with short text to see if it creates short segments
    print(f"\n3. 🧪 Testando alinhamento com texto curto...")
    
    short_texts = ["hi", "test", "hello", "ok"]
    
    for text in short_texts:
        print(f"\n   Testando com texto: '{text}'")
        
        try:
            aligner = AudioAligner()
            result = aligner.align_audio_to_text_enhanced(
                audio_path=audio_file,
                transcript=text,
                method="auto"
            )
            
            if result and isinstance(result, tuple) and len(result) >= 3:
                alignment_result, timeline, frame_states = result
                
                if timeline:
                    # Look for segments with duration around 556ms
                    for i, element in enumerate(timeline):
                        element_ms = element.duration * 1000
                        
                        if abs(element_ms - target_duration_ms) < tolerance*1000:
                            print(f"      ⭐ MATCH no elemento {i}: {element.word} - {element_ms:.0f}ms")
                        
                        if element.word != 'PAUSE' and element_ms < 1000:  # Words shorter than 1s
                            print(f"      Palavra curta: {element.word} - {element_ms:.0f}ms")
                
                # Check video duration
                if frame_states:
                    fps = 30.0
                    video_duration_ms = (len(frame_states) / fps) * 1000
                    
                    # Check if video duration matches 775ms
                    if abs(video_duration_ms - 775) < 50:  # 50ms tolerance
                        print(f"      🚨 PROBLEMA ENCONTRADO! Vídeo: {video_duration_ms:.0f}ms")
                        print(f"         Frames: {len(frame_states)}")
                        print(f"         Timeline elements: {len(timeline)}")
                        
                        # Detailed analysis
                        if timeline:
                            timeline_duration_ms = max([t.end_time for t in timeline]) * 1000
                            print(f"         Timeline duration: {timeline_duration_ms:.0f}ms")
                    
                    elif video_duration_ms < 1000:  # Short videos
                        print(f"      Vídeo curto: {video_duration_ms:.0f}ms")
        
        except Exception as e:
            print(f"      ❌ Erro: {e}")
    
    # 4. Check if there are any cached or intermediate files with these durations
    print(f"\n4. 📁 Verificando arquivos intermediários...")
    
    # Look in uploads and temp directories
    import glob
    patterns = ["uploads/**/*.mp4", "uploads/**/*.wav", "*.mp4", "temp_*.wav", "output_*.mp4"]
    
    all_media_files = []
    for pattern in patterns:
        all_media_files.extend(glob.glob(pattern, recursive=True))
    
    for media_file in all_media_files:
        if os.path.exists(media_file) and os.path.getsize(media_file) > 0:
            try:
                # For audio files
                if media_file.endswith(('.wav', '.mp3')):
                    audio_check, sr = librosa.load(media_file, sr=16000)
                    duration_ms = (len(audio_check) / sr) * 1000
                    
                    if abs(duration_ms - target_duration_ms) < tolerance*1000 or abs(duration_ms - 775) < 50:
                        print(f"      ⭐ MATCH: {media_file} - {duration_ms:.0f}ms")
                
                # For video files (estimate from file size and typical bitrate)
                elif media_file.endswith('.mp4'):
                    file_size = os.path.getsize(media_file)
                    # Rough estimation: typical video is ~1MB per minute at reasonable quality
                    estimated_duration_ms = (file_size / (1024*1024)) * 60 * 1000
                    
                    if estimated_duration_ms < 2000:  # Less than 2 seconds (could be our problem)
                        print(f"      Vídeo curto: {media_file} - ~{estimated_duration_ms:.0f}ms (estimativa)")
            
            except Exception as e:
                # Log the error instead of silently passing
                from logger import get_logger, log_exception
                debug_logger = get_logger('debug.measurements')
                log_exception(debug_logger, e, {'file': media_file})
                print(f"      ⚠️ Error processing {media_file}: {str(e)}")
    
    return True

if __name__ == "__main__":
    debug_specific_measurements()