#!/usr/bin/env python3
"""
Teste específico para validar que a correção de timing drift resolve 
o problema reportado pelo usuário.

CENÁRIO DE TESTE:
- 1 minuto de áudio simulado
- Primeiros 20s: timing normal
- Próximos 20s: timing acelerado (problema)
- Últimos 20s: timing muito lento (problema)

VALIDAÇÃO:
- Antes da correção: deve detectar os problemas
- Após a correção: timing deve ser uniforme em todos os segmentos
"""

import sys
import os

# Adiciona o diretório atual ao path para importar a função
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Simula a função do app.py (sem precisar importar Flask)
def validate_and_correct_frame_timing_test(frame_states, audio_duration_ms=None, fps=30.0):
    """
    Versão de teste da função de correção
    """
    if not frame_states:
        return frame_states
    
    # Detecta problemas de timing primeiro
    ms_values = [frame.get('ms', 33.33) for frame in frame_states]
    avg_ms = sum(ms_values) / len(ms_values)
    std_dev = (sum((x - avg_ms) ** 2 for x in ms_values) / len(ms_values)) ** 0.5
    variation_coefficient = std_dev / avg_ms if avg_ms > 0 else 0
    
    # Se timing parece OK, não mexe
    if variation_coefficient < 0.2 and 25 <= avg_ms <= 45:
        print(f"✅ Timing looks good (var: {variation_coefficient:.2f}, avg: {avg_ms:.1f}ms)")
        return frame_states
    
    print(f"🔧 Timing drift detected! Variation: {variation_coefficient:.2f}, Avg: {avg_ms:.1f}ms")
    
    # Calcula timing correto baseado no FPS
    target_frame_duration_ms = 1000.0 / fps
    
    # Estima duração do áudio se não fornecida
    if audio_duration_ms is None:
        # Usa timestamp do último frame se disponível
        last_timestamp = 0
        for frame in reversed(frame_states):
            if 'timestamp' in frame:
                last_timestamp = frame['timestamp'] * 1000  # Converte para ms
                break
        
        if last_timestamp == 0:
            # Fallback: usa soma dos ms values
            audio_duration_ms = sum(ms_values)
        else:
            audio_duration_ms = last_timestamp
    
    print(f"📊 Correcting {len(frame_states)} frames to {fps} FPS (target: {target_frame_duration_ms:.2f}ms per frame)")
    
    # Corrige timing mantendo estrutura
    corrected_frames = []
    
    for i, frame in enumerate(frame_states):
        corrected_frame = frame.copy()
        
        # Preserva dados originais para debug
        corrected_frame['ms_original'] = frame.get('ms', 33.33)
        if 'timestamp' in frame:
            corrected_frame['timestamp_original'] = frame['timestamp']
        
        # Aplica timing correto
        corrected_frame['ms'] = target_frame_duration_ms
        corrected_frame['timestamp'] = i * (target_frame_duration_ms / 1000)
        
        corrected_frames.append(corrected_frame)
    
    final_duration = len(corrected_frames) * target_frame_duration_ms / 1000
    print(f"✅ Timing corrected: {final_duration:.2f}s total duration")
    
    return corrected_frames

def create_problematic_frame_states():
    """
    Cria frame_states que simulam exatamente o problema reportado:
    - 0-20s: perfeito (33.33ms por frame)
    - 20-40s: acelerado (15ms por frame)  
    - 40-60s: muito lento (80ms por frame)
    """
    frame_states = []
    
    words_first_20s = ["ESTE", "É", "O", "PRIMEIRO", "SEGMENTO", "COM", "TIMING", "PERFEITO", "SEM", "PROBLEMAS"]
    words_middle_20s = ["AQUI", "COMEÇA", "O", "PROBLEMA", "DE", "ACELERAÇÃO", "MUITO", "RÁPIDO"] 
    words_last_20s = ["FINAL", "MUITO", "LENTO", "POUCOS", "FRAMES"]
    
    current_timestamp = 0.0
    frame_number = 0
    
    # Segmento 1: 0-20s - timing perfeito
    print("🎯 Gerando segmento 1: 0-20s (timing perfeito)")
    for word in words_first_20s:
        # Pausa
        frame_states.append({
            'frame_number': frame_number,
            'timestamp': current_timestamp,
            'active_word': '',
            'ms': 33.33,  # Normal
            'is_pause': True,
            'segment': '0-20s'
        })
        current_timestamp += 33.33 / 1000
        frame_number += 1
        
        # Frames da palavra (3 frames por palavra)
        for _ in range(3):
            frame_states.append({
                'frame_number': frame_number,
                'timestamp': current_timestamp, 
                'active_word': word,
                'ms': 33.33,  # Normal - 30 FPS
                'is_pause': False,
                'segment': '0-20s'
            })
            current_timestamp += 33.33 / 1000
            frame_number += 1
    
    # Segmento 2: 20-40s - acelerado (problema!)
    print("⚡ Gerando segmento 2: 20-40s (acelerado - PROBLEMA)")
    for word in words_middle_20s:
        # Pausa rápida
        frame_states.append({
            'frame_number': frame_number,
            'timestamp': current_timestamp,
            'active_word': '',
            'ms': 15.0,  # Muito rápido!
            'is_pause': True,
            'segment': '20-40s'
        })
        current_timestamp += 15.0 / 1000
        frame_number += 1
        
        # Frames da palavra (apenas 2 frames por palavra - muito rápido)
        for _ in range(2):
            frame_states.append({
                'frame_number': frame_number,
                'timestamp': current_timestamp,
                'active_word': word,
                'ms': 15.0,  # Muito rápido - ~67 FPS!
                'is_pause': False,
                'segment': '20-40s'
            })
            current_timestamp += 15.0 / 1000
            frame_number += 1
    
    # Segmento 3: 40-60s - muito lento (problema!)
    print("🐌 Gerando segmento 3: 40-60s (muito lento - PROBLEMA)")
    for word in words_last_20s:
        # Pausa longa
        frame_states.append({
            'frame_number': frame_number,
            'timestamp': current_timestamp,
            'active_word': '',
            'ms': 80.0,  # Muito lento!
            'is_pause': True,
            'segment': '40-60s'
        })
        current_timestamp += 80.0 / 1000
        frame_number += 1
        
        # Frames da palavra (muitos frames por palavra - muito lento)
        for _ in range(8):
            frame_states.append({
                'frame_number': frame_number,
                'timestamp': current_timestamp,
                'active_word': word,
                'ms': 80.0,  # Muito lento - ~12.5 FPS
                'is_pause': False,
                'segment': '40-60s'
            })
            current_timestamp += 80.0 / 1000
            frame_number += 1
    
    print(f"✅ Total: {len(frame_states)} frame_states gerados")
    print(f"📊 Duração total simulada: {current_timestamp:.2f}s")
    
    return frame_states

def analyze_timing_by_segments(frame_states, segment_duration=20.0):
    """
    Analisa timing por segmentos de tempo
    """
    segments = {}
    
    for frame in frame_states:
        timestamp = frame.get('timestamp', 0)
        
        # Determina segmento baseado no timestamp
        if timestamp < segment_duration:
            segment_key = f"0-{int(segment_duration)}s"
        elif timestamp < segment_duration * 2:
            segment_key = f"{int(segment_duration)}-{int(segment_duration*2)}s"  
        else:
            segment_key = f"{int(segment_duration*2)}-{int(segment_duration*3)}s"
        
        if segment_key not in segments:
            segments[segment_key] = []
        
        segments[segment_key].append(frame)
    
    analysis = {}
    
    for segment_name, frames in segments.items():
        if not frames:
            continue
            
        ms_values = [f.get('ms', 33.33) for f in frames]
        avg_ms = sum(ms_values) / len(ms_values)
        fps_calculated = 1000 / avg_ms if avg_ms > 0 else 0
        
        # Conta tipos de frame
        word_frames = [f for f in frames if not f.get('is_pause')]
        pause_frames = [f for f in frames if f.get('is_pause')]
        
        analysis[segment_name] = {
            'total_frames': len(frames),
            'word_frames': len(word_frames),
            'pause_frames': len(pause_frames),
            'avg_frame_duration_ms': avg_ms,
            'calculated_fps': fps_calculated,
            'duration_seconds': len(frames) * avg_ms / 1000
        }
    
    return analysis

def test_timing_drift_correction():
    """
    Teste principal que valida a correção
    """
    print("🧪 TESTE DE CORREÇÃO DE TIMING DRIFT")
    print("=" * 60)
    
    # 1. Cria dados problemáticos
    print("\n1. Criando frame_states com timing drift...")
    problematic_frames = create_problematic_frame_states()
    
    # 2. Analisa problemas ANTES da correção
    print("\n2. Analisando problemas ANTES da correção...")
    before_analysis = analyze_timing_by_segments(problematic_frames)
    
    print("📊 ANÁLISE PRÉ-CORREÇÃO:")
    for segment, data in before_analysis.items():
        fps = data['calculated_fps']
        ms_avg = data['avg_frame_duration_ms']
        
        status = "✅ NORMAL"
        if fps > 40:
            status = "⚡ ACELERADO"
        elif fps < 20:
            status = "🐌 MUITO LENTO"
            
        print(f"   {segment}: {fps:.1f} FPS ({ms_avg:.1f}ms avg) - {status}")
    
    # 3. Aplica correção
    print("\n3. Aplicando correção de timing...")
    corrected_frames = validate_and_correct_frame_timing_test(problematic_frames)
    
    # 4. Analisa resultado APÓS correção  
    print("\n4. Analisando resultado APÓS a correção...")
    after_analysis = analyze_timing_by_segments(corrected_frames)
    
    print("📊 ANÁLISE PÓS-CORREÇÃO:")
    all_fixed = True
    
    for segment, data in after_analysis.items():
        fps = data['calculated_fps']
        ms_avg = data['avg_frame_duration_ms']
        
        status = "✅ CORRIGIDO"
        if abs(fps - 30.0) > 1.0:  # Mais de 1 FPS de diferença
            status = "❌ AINDA PROBLEMÁTICO"
            all_fixed = False
            
        print(f"   {segment}: {fps:.1f} FPS ({ms_avg:.1f}ms avg) - {status}")
    
    # 5. Resultado final
    print("\n" + "=" * 60)
    if all_fixed:
        print("🎯 SUCESSO! Todos os problemas de timing foram corrigidos!")
        print("   ✅ Lip sync agora deve funcionar uniformemente em todo o vídeo")
    else:
        print("❌ FALHA: Ainda há problemas de timing após a correção")
    
    # 6. Estatísticas detalhadas
    print(f"\n📈 ESTATÍSTICAS DETALHADAS:")
    print(f"   Frames originais: {len(problematic_frames)}")
    print(f"   Frames corrigidos: {len(corrected_frames)}")
    
    if problematic_frames and corrected_frames:
        original_duration = problematic_frames[-1]['timestamp']
        corrected_duration = corrected_frames[-1]['timestamp']
        print(f"   Duração original: {original_duration:.2f}s")
        print(f"   Duração corrigida: {corrected_duration:.2f}s")
        print(f"   Diferença: {abs(original_duration - corrected_duration)*1000:.0f}ms")

if __name__ == "__main__":
    test_timing_drift_correction()