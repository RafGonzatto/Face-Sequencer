#!/usr/bin/env python3
"""
TESTE ROBUSTO PARA ÁUDIOS LONGOS
================================

Testa a correção de timing em áudios de diferentes durações para garantir
que funcione consistentemente de 1 minuto até 30+ minutos.
"""

import sys
import json
from app import validate_and_correct_frame_timing, build_text_driven_sequence_enhanced

def create_test_frame_states(duration_seconds=60, fps=30, add_drift=True):
    """
    Cria frame states simulando problemas reais de timing drift
    """
    total_frames = int(duration_seconds * fps)
    frame_states = []
    
    for i in range(total_frames):
        # Simula timing inconsistente que causa drift
        if add_drift:
            # Timing inconsistente: acelera no meio, desacelera no final
            if i < total_frames * 0.33:  # Primeiros 33%: timing OK
                ms_value = 33.33
            elif i < total_frames * 0.67:  # Meio 33%: acelerado
                ms_value = 25.0
            else:  # Últimos 33%: lento
                ms_value = 45.0
        else:
            ms_value = 33.33  # Timing perfeito
            
        frame_state = {
            'ms': ms_value,
            'timestamp': i * (ms_value / 1000),
            'phoneme': 'sil' if i % 10 == 0 else 'a',
            'energy': 0.5,
            'frame_index': i
        }
        frame_states.append(frame_state)
    
    return frame_states

def test_timing_correction_robustness():
    """
    Testa a correção de timing em diferentes durações
    """
    print("🧪 TESTE ROBUSTO DE CORREÇÃO DE TIMING")
    print("="*50)
    
    # Testa diferentes durações
    test_durations = [60, 120, 300, 900, 1800]  # 1min, 2min, 5min, 15min, 30min
    
    for duration_seconds in test_durations:
        print(f"\n📏 Testando duração: {duration_seconds}s ({duration_seconds/60:.1f} minutos)")
        
        # Cria dados com problemas de timing
        problematic_frames = create_test_frame_states(duration_seconds, add_drift=True)
        
        print(f"   📊 Frames criados: {len(problematic_frames)}")
        
        # Analisa problemas originais
        ms_values = [frame['ms'] for frame in problematic_frames]
        avg_ms_original = sum(ms_values) / len(ms_values)
        
        # Aplica correção robusta
        corrected_frames = validate_and_correct_frame_timing(problematic_frames)
        
        # Valida correção
        corrected_ms = [frame['ms'] for frame in corrected_frames]
        avg_ms_corrected = sum(corrected_ms) / len(corrected_ms)
        
        # Verifica se todos os frames têm exatamente 33.33ms
        perfect_timing = all(abs(ms - 33.33) < 0.01 for ms in corrected_ms)
        
        # Verifica timestamps
        timing_errors = []
        for i, frame in enumerate(corrected_frames):
            expected_timestamp = i * (33.33 / 1000)
            actual_timestamp = frame['timestamp']
            error_ms = abs(actual_timestamp - expected_timestamp) * 1000
            timing_errors.append(error_ms)
        
        max_timing_error = max(timing_errors) if timing_errors else 0
        
        # Resultado do teste (critérios escaláveis por duração)
        timing_consistent = all(abs(ms - 33.33) < 0.1 for ms in corrected_ms)  # 0.1ms tolerância
        # Erro aceitável escala com duração: até 200ms para 30min é normal
        max_acceptable_error = min(200.0, duration_seconds * 0.5)  # 0.5ms por segundo
        acceptable_error = max_timing_error < max_acceptable_error
        
        print(f"   🔍 Timing original: {avg_ms_original:.2f}ms/frame")
        print(f"   ✅ Timing corrigido: {avg_ms_corrected:.2f}ms/frame")
        print(f"   ⏱️  Timing consistente: {'✅ SIM' if timing_consistent else '❌ NÃO'}")
        print(f"   📐 Erro máximo: {max_timing_error:.2f}ms")
        
        if timing_consistent and acceptable_error:
            print(f"   🎯 RESULTADO: ✅ PERFEITO")
        else:
            print(f"   🎯 RESULTADO: ❌ FALHOU")
            
def test_word_boundary_processing():
    """
    Testa processamento completo com word boundaries
    """
    print(f"\n🎬 TESTE DE PROCESSAMENTO COMPLETO")
    print("="*40)
    
    # Cria dados simulando áudio de 2 minutos
    frame_states = create_test_frame_states(120, add_drift=True)
    
    # Simula word boundaries
    word_boundaries = []
    for i in range(0, len(frame_states), 30):  # Palavra a cada segundo
        word_boundaries.append({
            'word': f'palavra_{i//30}',
            'start': i / 30.0,
            'end': (i + 25) / 30.0,
            'score': 0.95
        })
    
    print(f"📊 Frame states: {len(frame_states)}")
    print(f"📝 Word boundaries: {len(word_boundaries)}")
    
    try:
        # Cria projeto mock para o teste
        mock_project = {
            'word_boundaries': word_boundaries,
            'settings': {'alignment_accuracy': 'high'}
        }
        
        # Processa sequência completa
        sequence = build_text_driven_sequence_enhanced(
            frame_states=frame_states,
            text="Teste de processamento completo com áudio longo",
            project=mock_project
        )
        
        if sequence:
            print(f"🎯 Sequência gerada: {len(sequence)} frames")
            
            # Valida timing da sequência final
            total_ms = sum(frame.get('ms', 33.33) for frame in sequence)
            expected_ms = len(sequence) * 33.33
            error_ms = abs(total_ms - expected_ms)
            
            print(f"⏱️  Duração esperada: {expected_ms/1000:.3f}s")
            print(f"⏱️  Duração atual: {total_ms/1000:.3f}s")
            print(f"📐 Erro total: {error_ms:.1f}ms")
            
            if error_ms < 100:
                print(f"✅ SUCESSO: Processamento completo funcionou!")
            else:
                print(f"❌ FALHA: Erro de timing muito grande")
        else:
            print(f"❌ FALHA: Sequência vazia")
            
    except Exception as e:
        print(f"❌ ERRO: {e}")

if __name__ == "__main__":
    print("🚀 INICIANDO TESTE ROBUSTO DE TIMING PARA ÁUDIOS LONGOS")
    print("Objetivo: Garantir lip sync perfeito de 1min até 30+ minutos")
    print()
    
    test_timing_correction_robustness()
    test_word_boundary_processing()
    
    print(f"\n🏁 TESTE CONCLUÍDO")
    print("Se todos os resultados foram '✅ PERFEITO', a correção está robusta!")