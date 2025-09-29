#!/usr/bin/env python3
"""
Análise avançada do problema de timing drift persistente.

PROBLEMA ATUALIZADO:
- Primeiros 40s: funciona corretamente 
- Após 40s: volta a ter lip sync errado, desconexo, frames trocados e lento
- Deve funcionar consistentemente em áudios de 1min até +30min

HIPÓTESES PARA INVESTIGAR:
1. Drift residual no cálculo cumulativo mesmo após correção
2. Problema na distribuição de frames por palavra em segmentos longos  
3. Acúmulo de pequenos erros de arredondamento ao longo do tempo
4. Inconsistência entre word boundaries e frame distribution
"""

import math
from typing import List, Dict, Any

def diagnose_advanced_timing_issues():
    """
    Diagnóstico avançado para identificar o problema após 40s
    """
    print("🔬 DIAGNÓSTICO AVANÇADO DE TIMING DRIFT")
    print("=" * 60)
    
    # Simula o cenário real: 40s funcionam, depois quebra
    frame_states_1min = create_realistic_frame_states(duration_seconds=60)
    
    print(f"\n📊 Simulação: {len(frame_states_1min)} frames para 60s")
    
    # Aplica a correção atual
    corrected_frames = apply_current_correction(frame_states_1min)
    
    # Analisa timing por segmentos de 10s  
    segments_analysis = analyze_by_segments(corrected_frames, segment_duration=10.0)
    
    print(f"\n📈 ANÁLISE POR SEGMENTOS (10s cada):")
    for segment_name, data in segments_analysis.items():
        fps = data.get('fps_actual', 0)
        consistency = "✅ OK" if 25 <= fps <= 35 else "❌ PROBLEMA"
        print(f"   {segment_name}: {fps:.1f} FPS - {consistency}")
    
    # Identifica onde o problema começa
    problem_segments = []
    for segment_name, data in segments_analysis.items():
        if data.get('fps_actual', 30) < 25 or data.get('fps_actual', 30) > 35:
            problem_segments.append(segment_name)
    
    if problem_segments:
        print(f"\n❌ PROBLEMAS DETECTADOS EM: {', '.join(problem_segments)}")
        print("   → Confirma que o problema persiste em segmentos específicos")
    
    # Analisa drift cumulativo
    cumulative_drift = analyze_cumulative_drift(corrected_frames)
    
    print(f"\n📊 DRIFT CUMULATIVO:")
    for timestamp, drift_ms in cumulative_drift.items():
        status = "✅ OK" if abs(drift_ms) < 100 else "❌ DRIFT"
        print(f"   {timestamp:2.0f}s: {drift_ms:+.1f}ms - {status}")
    
    return {
        'segments_analysis': segments_analysis,
        'problem_segments': problem_segments,
        'cumulative_drift': cumulative_drift,
        'needs_advanced_fix': len(problem_segments) > 0
    }

def create_realistic_frame_states(duration_seconds=60, base_fps=30):
    """
    Cria frame_states realistas que simulam o problema real
    """
    frame_states = []
    words = [
        "ESTE", "É", "UM", "TESTE", "COMPLETO", "DE", "ALINHAMENTO", 
        "PARA", "VERIFICAR", "SE", "O", "TIMING", "PERMANECE", "ESTÁVEL",
        "DURANTE", "TODO", "O", "ÁUDIO", "SEM", "QUEBRAR", "APÓS", "QUARENTA",
        "SEGUNDOS", "COMO", "ACONTECIA", "ANTERIORMENTE", "COM", "O", "SISTEMA"
    ] * 10  # Repete para ter palavras suficientes
    
    current_time = 0.0
    frame_number = 0
    
    for i, word in enumerate(words):
        if current_time >= duration_seconds:
            break
            
        # Simula problema que volta após 40s
        if current_time < 40.0:
            # Primeiros 40s: timing correto
            word_duration = 0.8  # 800ms
            frames_per_word = 24  # ~30 FPS
            frame_ms = 33.33
        else:
            # Após 40s: problema volta (simula o bug real)
            word_duration = 0.6  # 600ms 
            frames_per_word = 40  # Muitos frames = lento
            frame_ms = 15.0  # Inconsistente
        
        # Pausa antes da palavra
        frame_states.append({
            'frame_number': frame_number,
            'timestamp': current_time,
            'active_word': '',
            'ms': frame_ms,
            'is_pause': True,
            'segment': f"{int(current_time//10)*10}-{int(current_time//10)*10+10}s"
        })
        current_time += frame_ms / 1000
        frame_number += 1
        
        # Frames da palavra
        for f in range(frames_per_word):
            frame_states.append({
                'frame_number': frame_number,
                'timestamp': current_time,
                'active_word': word,
                'ms': frame_ms,
                'is_pause': False,
                'segment': f"{int(current_time//10)*10}-{int(current_time//10)*10+10}s"
            })
            current_time += frame_ms / 1000
            frame_number += 1
    
    return frame_states

def apply_current_correction(frame_states):
    """
    Aplica a correção atual para ver se é suficiente
    """
    if not frame_states:
        return frame_states
    
    # Detecta problemas de timing primeiro
    ms_values = [frame.get('ms', 33.33) for frame in frame_states]
    avg_ms = sum(ms_values) / len(ms_values)
    std_dev = (sum((x - avg_ms) ** 2 for x in ms_values) / len(ms_values)) ** 0.5
    variation_coefficient = std_dev / avg_ms if avg_ms > 0 else 0
    
    print(f"🔍 Variação detectada: {variation_coefficient:.3f} (limite: 0.2)")
    
    # Se timing parece OK, não mexe (PROBLEMA: pode não detectar drift sutil!)
    if variation_coefficient < 0.2 and 25 <= avg_ms <= 45:
        print("⚠️  AVISO: Correção atual não aplicada - critério muito permissivo!")
        return frame_states
    
    # Aplica correção simples
    target_ms = 1000.0 / 30.0  # 30 FPS
    
    corrected_frames = []
    for i, frame in enumerate(frame_states):
        corrected_frame = frame.copy()
        corrected_frame['ms_original'] = frame.get('ms', 33.33)
        corrected_frame['ms'] = target_ms
        corrected_frame['timestamp'] = i * (target_ms / 1000)
        corrected_frames.append(corrected_frame)
    
    return corrected_frames

def analyze_by_segments(frame_states, segment_duration=10.0):
    """
    Analisa timing por segmentos específicos
    """
    segments = {}
    
    for frame in frame_states:
        timestamp = frame.get('timestamp', 0)
        segment_idx = int(timestamp // segment_duration)
        segment_name = f"{segment_idx*segment_duration:.0f}-{(segment_idx+1)*segment_duration:.0f}s"
        
        if segment_name not in segments:
            segments[segment_name] = []
        segments[segment_name].append(frame)
    
    analysis = {}
    for segment_name, frames in segments.items():
        if not frames:
            continue
            
        ms_values = [f.get('ms', 33.33) for f in frames]
        avg_ms = sum(ms_values) / len(ms_values)
        fps_actual = 1000 / avg_ms if avg_ms > 0 else 0
        
        # Calcula drift interno do segmento
        expected_frames = segment_duration * 30  # 30 FPS esperado
        actual_frames = len(frames)
        frame_drift = actual_frames - expected_frames
        
        analysis[segment_name] = {
            'frames': len(frames),
            'avg_ms': avg_ms,
            'fps_actual': fps_actual,
            'frame_drift': frame_drift,
            'has_problem': abs(fps_actual - 30) > 5
        }
    
    return analysis

def analyze_cumulative_drift(frame_states):
    """
    Analisa drift cumulativo ao longo do tempo
    """
    drift_analysis = {}
    
    for i, frame in enumerate(frame_states):
        timestamp = frame.get('timestamp', 0)
        
        # A cada 10 segundos, verifica o drift
        if i % 300 == 0:  # ~300 frames = 10s @ 30fps
            expected_time = i / 30.0  # Tempo esperado @ 30fps
            actual_time = timestamp
            drift_ms = (actual_time - expected_time) * 1000
            
            drift_analysis[timestamp] = drift_ms
    
    return drift_analysis

def design_robust_correction():
    """
    Projeta uma correção robusta baseada na análise
    """
    return """
🎯 CORREÇÃO ROBUSTA NECESSÁRIA:

PROBLEMAS IDENTIFICADOS:
1. Correção atual é muito permissiva (só atua se variação > 20%)
2. Drift cumulativo se acumula mesmo com correção básica  
3. Word boundary calculation pode estar causando inconsistências
4. Não há validação contínua durante o processamento

SOLUÇÃO AVANÇADA:

1. TIMING MASTER ABSOLUTO:
   - Usar apenas FPS e posição de frame como fonte de verdade
   - Ignorar completamente valores 'ms' dos frame_states originais
   - Recalcular TODOS os timestamps desde zero

2. VALIDAÇÃO CONTÍNUA:
   - Verificar drift a cada 1000 frames (~33s @ 30fps)
   - Aplicar micro-correções quando drift > 50ms
   - Log detalhado para debug

3. WORD BOUNDARY INDEPENDENTE:
   - Calcular word boundaries baseado em timing absoluto
   - Não depender de timestamps originais dos frames
   - Validar consistência entre boundaries e frames

4. DISTRIBUIÇÃO MATEMÁTICA:
   - Usar distribuição linear matemática para tokens
   - Evitar lógica complexa que pode introduzir errors
   - Garantir que última palavra alcança final exato

IMPLEMENTAÇÃO:
```python
def validate_and_correct_frame_timing_v2(frame_states, fps=30.0):
    # FORÇA timing absoluto - não confia em dados originais
    target_ms = 1000.0 / fps
    
    for i, frame in enumerate(frame_states):
        # FORÇA timestamp correto independente do original
        frame['timestamp'] = i * (target_ms / 1000) 
        frame['ms'] = target_ms
        
        # Validação a cada 1000 frames
        if i % 1000 == 0 and i > 0:
            expected_time = i / fps
            if abs(frame['timestamp'] - expected_time) > 0.05:  # 50ms
                print(f"⚠️ Drift detected at frame {i}, correcting...")
                # Recorrige todos os frames subsequentes
```
"""

def main():
    diagnosis = diagnose_advanced_timing_issues()
    
    print("\n" + "=" * 60)
    print("🎯 CONCLUSÃO:")
    
    if diagnosis['needs_advanced_fix']:
        print("❌ Correção atual é INSUFICIENTE!")
        print("   → Problema persiste após 40s conforme reportado")
        print("   → Necessária correção mais robusta")
        
        solution = design_robust_correction()
        print(solution)
    else:
        print("✅ Correção atual seria suficiente")
        print("   → Problema pode estar em outro lugar")

if __name__ == "__main__":
    main()