#!/usr/bin/env python3
"""
Investigar os vídeos curtos gerados, especialmente direct_test.mp4
"""

import os
import subprocess
import json

def investigate_short_videos():
    """Investigar vídeos curtos para entender o problema de timing"""
    
    print("🔍 Investigando vídeos curtos gerados...")
    
    # List of short video files found
    short_videos = [
        "direct_test.mp4",
        "custom_writer_output.mp4", 
        "test_direct_ffmpeg.mp4"
    ]
    
    for video_file in short_videos:
        if os.path.exists(video_file):
            print(f"\n📹 Analisando: {video_file}")
            
            # Get file size
            file_size = os.path.getsize(video_file)
            print(f"   Tamanho do arquivo: {file_size} bytes ({file_size/1024:.1f} KB)")
            
            # Use ffprobe to get exact video information
            try:
                cmd = [
                    'ffprobe', '-v', 'quiet', '-print_format', 'json',
                    '-show_format', '-show_streams', video_file
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    data = json.loads(result.stdout)
                    
                    # Extract video information
                    format_info = data.get('format', {})
                    duration = format_info.get('duration', '0')
                    
                    print(f"   Duração real: {float(duration):.3f}s ({float(duration)*1000:.0f}ms)")
                    print(f"   Bitrate: {format_info.get('bit_rate', 'N/A')}")
                    
                    # Video stream info
                    video_streams = [s for s in data.get('streams', []) if s.get('codec_type') == 'video']
                    if video_streams:
                        video_stream = video_streams[0]
                        fps = eval(video_stream.get('r_frame_rate', '0/1'))
                        width = video_stream.get('width', 0)
                        height = video_stream.get('height', 0)
                        
                        print(f"   Resolução: {width}x{height}")
                        print(f"   FPS: {fps:.2f}")
                        
                        # Calculate total frames
                        total_frames = int(float(duration) * fps)
                        print(f"   Total frames: {total_frames}")
                        
                        # Check if this matches our problem
                        duration_ms = float(duration) * 1000
                        
                        if abs(duration_ms - 556) < 50:  # Within 50ms of 556ms
                            print(f"   🚨 PROBLEMA ENCONTRADO! Este vídeo tem ~556ms!")
                        
                        if abs(duration_ms - 775) < 50:  # Within 50ms of 775ms  
                            print(f"   🚨 PROBLEMA ENCONTRADO! Este vídeo tem ~775ms!")
                        
                        # Check if duration seems wrong
                        if duration_ms < 1000:  # Very short video
                            print(f"   ⚠️  Vídeo muito curto - possível problema")
                
                else:
                    print(f"   ❌ Erro ao analisar com ffprobe: {result.stderr}")
            
            except Exception as e:
                print(f"   ❌ Erro ao executar ffprobe: {e}")
            
            # Check modification time to see when it was created
            mtime = os.path.getmtime(video_file)
            import datetime
            mod_time = datetime.datetime.fromtimestamp(mtime)
            print(f"   Criado/modificado: {mod_time}")
        
        else:
            print(f"\n📹 {video_file}: Arquivo não encontrado")
    
    # Also check if there are any recent MP4 files
    print(f"\n📁 Verificando outros arquivos MP4 recentes...")
    
    import glob
    mp4_files = glob.glob("*.mp4") + glob.glob("uploads/**/*.mp4", recursive=True)
    
    for mp4_file in mp4_files:
        if mp4_file not in short_videos and os.path.exists(mp4_file):
            file_size = os.path.getsize(mp4_file)
            
            # Only check small files (likely to be short duration)
            if file_size < 1024 * 1024:  # Less than 1MB
                print(f"   {mp4_file}: {file_size} bytes")
                
                # Quick estimate of duration based on file size
                # Typical video is ~1MB per minute, so small files are very short
                estimated_seconds = (file_size / (1024 * 1024)) * 60
                estimated_ms = estimated_seconds * 1000
                
                if estimated_ms < 2000:  # Less than 2 seconds
                    print(f"      Estimativa: {estimated_ms:.0f}ms (muito curto!)")
                    
                    if abs(estimated_ms - 556) < 200 or abs(estimated_ms - 775) < 200:
                        print(f"      🎯 POSSÍVEL MATCH para o problema reportado!")

def check_frame_synchronizer_issues():
    """Verificar se há problemas no frame synchronizer"""
    
    print(f"\n🔍 Verificando possíveis problemas no frame synchronizer...")
    
    # Check if there are any issues with timing calculations
    from frame_synchronizer import PreciseFrameSynchronizer
    
    # Create a test timeline with problematic duration patterns
    synchronizer = PreciseFrameSynchronizer(fps=30.0)
    
    # Test with various FPS values to see if there are rounding issues
    fps_values = [24, 25, 30, 60]
    test_durations = [0.556, 0.775, 1.0, 2.0]  # Include the problematic durations
    
    for fps in fps_values:
        for duration in test_durations:
            expected_frames = int(duration * fps)
            calculated_duration = expected_frames / fps
            
            print(f"   FPS {fps}, Duration {duration}s: {expected_frames} frames = {calculated_duration:.3f}s")
            
            if abs(calculated_duration - duration) > 0.001:  # More than 1ms difference
                print(f"      ⚠️  Rounding error: {abs(calculated_duration - duration)*1000:.1f}ms")

if __name__ == "__main__":
    investigate_short_videos()
    check_frame_synchronizer_issues()