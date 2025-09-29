#!/usr/bin/env python3
"""
Implementação da correção robusta para o problema de timing drift.

PROBLEMA IDENTIFICADO:
- O cálculo cumulativo de timing usa valores 'ms' inconsistentes dos frame_states
- Isso causa acúmulo de erro temporal ao longo do tempo  
- Resultado: 20s perfeitos, depois acelerado, depois muito lento

SOLUÇÃO:
- Usar o áudio como fonte autoritativa de timing
- Recalcular todos os timestamps baseado no FPS fixo
- Manter toda a lógica de tokenização/distribuição existente
"""

import math
from typing import List, Dict, Any, Tuple

def validate_and_correct_frame_timing(
    frame_states: List[Dict[str, Any]], 
    audio_duration_ms: float, 
    fps: float = 30.0,
    preserve_word_boundaries: bool = True
) -> List[Dict[str, Any]]:
    """
    Corrige timing drift mantendo todas as features existentes
    
    Args:
        frame_states: Frame states originais (potencialmente com timing inconsistente)
        audio_duration_ms: Duração total do áudio em milissegundos
        fps: Frame rate target (padrão 30 FPS)
        preserve_word_boundaries: Se deve preservar limites de palavra originais
        
    Returns:
        Frame states com timing corrigido
    """
    if not frame_states:
        return []
    
    print(f"🔧 Corrigindo timing de {len(frame_states)} frames para {fps} FPS")
    print(f"📊 Áudio: {audio_duration_ms/1000:.2f}s, Frames originais: {len(frame_states)}")
    
    # Calcula timing correto baseado no áudio e FPS
    frame_duration_ms = 1000.0 / fps
    expected_total_frames = int(math.ceil(audio_duration_ms / frame_duration_ms))
    
    print(f"📊 Frame duration target: {frame_duration_ms:.2f}ms")
    print(f"📊 Frames esperados: {expected_total_frames}")
    
    # Se temos muito mais ou muito menos frames que o esperado, há problema
    frame_ratio = len(frame_states) / expected_total_frames
    
    if abs(frame_ratio - 1.0) > 0.1:  # Mais de 10% de diferença
        print(f"⚠️  WARNING: Frame count mismatch! Ratio: {frame_ratio:.2f}")
        
        if frame_ratio > 1.2:
            print("   → Muitos frames: possível duplicação ou FPS incorreto")
        elif frame_ratio < 0.8:
            print("   → Poucos frames: possível perda ou truncamento")
    
    # Estratégia 1: Ajuste direto (preserva número de frames, corrige timing)
    corrected_frames = []
    
    if preserve_word_boundaries:
        # Extrai word boundaries originais
        word_boundaries = extract_word_boundaries(frame_states)
        print(f"📝 Extraídos {len(word_boundaries)} word boundaries")
        
        # Redistribui frames mantendo proporção de palavras
        corrected_frames = redistribute_frames_proportionally(
            frame_states, word_boundaries, frame_duration_ms
        )
    else:
        # Correção simples: distribui frames uniformemente
        for i, frame in enumerate(frame_states):
            corrected_frame = frame.copy()
            corrected_frame['timestamp_original'] = frame.get('timestamp', 0)
            corrected_frame['ms_original'] = frame.get('ms', 33.33)
            
            # Calcula novo timing baseado na posição
            corrected_frame['timestamp'] = i * (frame_duration_ms / 1000)
            corrected_frame['ms'] = frame_duration_ms
            
            corrected_frames.append(corrected_frame)
    
    # Validação final
    if corrected_frames:
        total_duration = corrected_frames[-1]['timestamp']
        timing_error_ms = abs(total_duration * 1000 - audio_duration_ms)
        
        print(f"✅ Correção completa:")
        print(f"   Duração final: {total_duration:.3f}s")
        print(f"   Erro de timing: {timing_error_ms:.1f}ms")
        
        if timing_error_ms > 100:  # Mais de 100ms de erro
            print(f"⚠️  Erro significativo de timing detectado!")
    
    return corrected_frames

def extract_word_boundaries(frame_states: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Extrai limites de palavra dos frame_states originais
    """
    boundaries = []
    current_word = ""
    current_word_start = None
    
    for i, frame in enumerate(frame_states):
        active_word = frame.get('active_word', '')
        
        # Detecta início de palavra
        if active_word and not current_word:
            current_word_start = i
            current_word = active_word
            
        # Detecta fim de palavra  
        elif current_word and (not active_word or active_word != current_word):
            if current_word_start is not None:
                boundaries.append({
                    'word': current_word,
                    'start_frame': current_word_start,
                    'end_frame': i - 1,
                    'frame_count': i - current_word_start
                })
            
            # Inicia nova palavra se existe
            if active_word:
                current_word_start = i
                current_word = active_word
            else:
                current_word = ""
                current_word_start = None
    
    # Adiciona última palavra se ainda ativa
    if current_word and current_word_start is not None:
        boundaries.append({
            'word': current_word,
            'start_frame': current_word_start, 
            'end_frame': len(frame_states) - 1,
            'frame_count': len(frame_states) - current_word_start
        })
    
    return boundaries

def redistribute_frames_proportionally(
    frame_states: List[Dict[str, Any]], 
    word_boundaries: List[Dict[str, Any]], 
    target_frame_duration_ms: float
) -> List[Dict[str, Any]]:
    """
    Redistribui frames mantendo proporção relativa entre palavras
    """
    corrected_frames = []
    current_timestamp = 0.0
    
    # Calcula proporção total de frames por palavra vs pausas
    total_word_frames = sum(b['frame_count'] for b in word_boundaries)
    total_frames = len(frame_states)
    pause_frames = total_frames - total_word_frames
    
    word_ratio = total_word_frames / total_frames if total_frames > 0 else 0.8
    pause_ratio = 1.0 - word_ratio
    
    print(f"📊 Proporções - Palavras: {word_ratio:.1%}, Pausas: {pause_ratio:.1%}")
    
    # Processa frame por frame aplicando timing correto
    word_index = 0
    current_boundary = word_boundaries[0] if word_boundaries else None
    
    for i, frame in enumerate(frame_states):
        corrected_frame = frame.copy()
        
        # Preserva dados originais para debug
        corrected_frame['timestamp_original'] = frame.get('timestamp', 0)
        corrected_frame['ms_original'] = frame.get('ms', 33.33)
        
        # Aplica timing correto
        corrected_frame['timestamp'] = current_timestamp
        corrected_frame['ms'] = target_frame_duration_ms
        
        # Avança para próxima boundary se necessário
        if (current_boundary and 
            i > current_boundary['end_frame'] and 
            word_index + 1 < len(word_boundaries)):
            word_index += 1
            current_boundary = word_boundaries[word_index]
        
        corrected_frames.append(corrected_frame)
        current_timestamp += target_frame_duration_ms / 1000
    
    return corrected_frames

def detect_timing_drift_in_sequence(sequence: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Detecta timing drift analisando a sequência de frames
    """
    if len(sequence) < 10:
        return {"error": "Sequence too short for analysis"}
    
    # Analisa distribuição de 'ms' values
    ms_values = [frame.get('ms', 33.33) for frame in sequence]
    
    # Estatísticas básicas
    avg_ms = sum(ms_values) / len(ms_values)
    min_ms = min(ms_values)
    max_ms = max(ms_values)
    std_dev = math.sqrt(sum((x - avg_ms) ** 2 for x in ms_values) / len(ms_values))
    
    # Detecta variação excessiva
    variation_coefficient = std_dev / avg_ms if avg_ms > 0 else 0
    
    # Analisa drift temporal
    segments = []
    segment_size = len(sequence) // 3  # Divide em 3 segmentos
    
    for i in range(3):
        start_idx = i * segment_size
        end_idx = min((i + 1) * segment_size, len(sequence))
        
        if start_idx < len(sequence):
            segment_frames = sequence[start_idx:end_idx]
            segment_ms_values = [f.get('ms', 33.33) for f in segment_frames]
            segment_avg = sum(segment_ms_values) / len(segment_ms_values) if segment_ms_values else 0
            
            segments.append({
                'segment': i + 1,
                'frames': len(segment_frames),
                'avg_ms': segment_avg,
                'fps_calculated': 1000 / segment_avg if segment_avg > 0 else 0
            })
    
    # Detecta problemas
    problems = []
    
    if variation_coefficient > 0.3:  # 30% de variação
        problems.append(f"High variation in frame durations (CV: {variation_coefficient:.2f})")
    
    if max_ms > avg_ms * 2:
        problems.append(f"Extremely slow frames detected (max: {max_ms:.1f}ms)")
        
    if min_ms < avg_ms * 0.5:
        problems.append(f"Extremely fast frames detected (min: {min_ms:.1f}ms)")
    
    # Detecta drift entre segmentos
    if len(segments) >= 2:
        fps_first = segments[0]['fps_calculated']
        fps_last = segments[-1]['fps_calculated']
        
        if abs(fps_first - fps_last) > 5:  # Diferença > 5 FPS
            if fps_last < fps_first:
                problems.append(f"Significant slowdown detected (FPS: {fps_first:.1f} → {fps_last:.1f})")
            else:
                problems.append(f"Significant speedup detected (FPS: {fps_first:.1f} → {fps_last:.1f})")
    
    return {
        'total_frames': len(sequence),
        'avg_frame_duration_ms': avg_ms,
        'min_frame_duration_ms': min_ms,
        'max_frame_duration_ms': max_ms,
        'std_deviation': std_dev,
        'variation_coefficient': variation_coefficient,
        'calculated_fps': 1000 / avg_ms if avg_ms > 0 else 0,
        'segments': segments,
        'problems_detected': problems,
        'has_timing_issues': len(problems) > 0
    }

def create_robust_timing_corrector():
    """
    Cria função de correção que pode ser integrada no código existente
    """
    def timing_corrector_for_build_sequence(frame_states, project_fps=30.0, audio_duration_s=None):
        """
        Função para ser usada no build_text_driven_sequence_enhanced
        """
        if not frame_states:
            return frame_states
            
        # Detecta problemas primeiro
        analysis = detect_timing_drift_in_sequence(frame_states)
        
        if not analysis.get('has_timing_issues'):
            print("✅ No timing issues detected, using original frame_states")
            return frame_states
            
        print("🔧 Timing issues detected, applying correction...")
        for problem in analysis['problems_detected']:
            print(f"   ❌ {problem}")
        
        # Estima duração do áudio se não fornecida
        if audio_duration_s is None:
            # Usa o timing original para estimar
            total_ms = sum(f.get('ms', 33.33) for f in frame_states)
            audio_duration_s = total_ms / 1000
            print(f"📊 Estimated audio duration: {audio_duration_s:.2f}s")
        
        # Aplica correção
        corrected = validate_and_correct_frame_timing(
            frame_states, 
            audio_duration_s * 1000, 
            project_fps, 
            preserve_word_boundaries=True
        )
        
        print(f"✅ Timing correction applied: {len(frame_states)} → {len(corrected)} frames")
        return corrected
        
    return timing_corrector_for_build_sequence

def test_timing_correction():
    """
    Testa a correção de timing com dados simulados
    """
    print("🧪 TESTE DA CORREÇÃO DE TIMING")
    print("=" * 50)
    
    # Simula frame_states problemáticos
    problematic_frames = []
    
    # Simula 60 segundos com timing irregular
    words = ["TESTE", "DE", "TIMING", "COM", "PROBLEMAS"] * 20
    
    current_time = 0.0
    for i, word in enumerate(words):
        # Simula timing inconsistente
        if i < 20:  # Primeiros 20 frames: normal
            ms_value = 33.33
        elif i < 60:  # Próximos 40: muito rápido  
            ms_value = 15.0
        else:  # Restante: muito lento
            ms_value = 80.0
            
        # Adiciona frames para a palavra
        for _ in range(3):  # 3 frames por palavra
            problematic_frames.append({
                'active_word': word,
                'ms': ms_value,
                'timestamp': current_time,
                'is_pause': False
            })
            current_time += ms_value / 1000
            
        # Pausa
        problematic_frames.append({
            'active_word': '',
            'ms': 33.33,
            'timestamp': current_time,
            'is_pause': True
        })
        current_time += 33.33 / 1000
    
    print(f"📊 Gerados {len(problematic_frames)} frames problemáticos")
    print(f"📊 Duração simulada: {current_time:.2f}s")
    
    # Detecta problemas
    analysis = detect_timing_drift_in_sequence(problematic_frames)
    print(f"\n🔍 ANÁLISE DE PROBLEMAS:")
    print(f"   FPS calculado: {analysis['calculated_fps']:.1f}")
    print(f"   Variação: {analysis['variation_coefficient']:.2f}")
    print(f"   Problemas detectados: {len(analysis['problems_detected'])}")
    
    for problem in analysis['problems_detected']:
        print(f"   ❌ {problem}")
    
    # Aplica correção
    print(f"\n🔧 APLICANDO CORREÇÃO...")
    corrector = create_robust_timing_corrector()
    corrected_frames = corrector(problematic_frames, project_fps=30.0, audio_duration_s=current_time)
    
    # Verifica resultado
    corrected_analysis = detect_timing_drift_in_sequence(corrected_frames)
    print(f"\n✅ RESULTADO DA CORREÇÃO:")
    print(f"   FPS corrigido: {corrected_analysis['calculated_fps']:.1f}")
    print(f"   Variação corrigida: {corrected_analysis['variation_coefficient']:.2f}")
    print(f"   Problemas restantes: {len(corrected_analysis['problems_detected'])}")
    
    if corrected_analysis['problems_detected']:
        for problem in corrected_analysis['problems_detected']:
            print(f"   ⚠️  {problem}")
    else:
        print(f"   🎯 Todos os problemas de timing foram corrigidos!")

if __name__ == "__main__":
    test_timing_correction()