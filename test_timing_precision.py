#!/usr/bin/env python3
"""
Teste específico para verificar timing preciso
"""

import sys
import os

# Adiciona o diretório atual ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_timing_precision():
    """Testa se o timing está sendo preservado corretamente"""
    
    print("🕒 TESTE DE PRECISÃO DE TIMING")
    print("=" * 50)
    
    # Cria frame_states com timing conhecido
    frame_states = [
        {'active_word': 'TESTE', 'ms': 100.0, 'is_pause': False},
        {'active_word': 'TESTE', 'ms': 150.0, 'is_pause': False},
        {'active_word': 'TESTE', 'ms': 200.0, 'is_pause': False},
        {'active_word': '', 'ms': 50.0, 'is_pause': True},
        {'active_word': 'FINAL', 'ms': 300.0, 'is_pause': False},
    ]
    
    expected_total = sum(f['ms'] for f in frame_states)
    
    mock_project = {
        'letter_map': {chr(i): f'{chr(i)}.png' for i in range(ord('A'), ord('Z')+1)},
        'special_tokens': {},
        'fallback_image': 'fallback.png',
        'pause_image': 'pause.png'
    }
    
    print(f"📊 Input: {len(frame_states)} frames")
    print(f"⏱️ Expected duration: {expected_total}ms")
    
    # Testa o alinhamento
    try:
        from app import build_text_driven_sequence_enhanced
        
        sequence = build_text_driven_sequence_enhanced(
            frame_states,
            "TESTE FINAL",
            mock_project
        )
        
        actual_total = sum(f['ms'] for f in sequence)
        
        print(f"✅ Output: {len(sequence)} frames")
        print(f"⏱️ Actual duration: {actual_total}ms")
        print(f"📊 Difference: {abs(expected_total - actual_total)}ms")
        
        # Verifica frame por frame
        print(f"\n🔍 ANÁLISE FRAME POR FRAME:")
        for i, (input_frame, output_frame) in enumerate(zip(frame_states, sequence)):
            input_ms = input_frame['ms']
            output_ms = output_frame['ms']
            
            if abs(input_ms - output_ms) > 0.1:  # Tolerância de 0.1ms
                print(f"  Frame {i}: {input_ms}ms -> {output_ms}ms ❌")
            else:
                print(f"  Frame {i}: {input_ms}ms -> {output_ms}ms ✅")
        
        # Verifica se há frames extras
        if len(sequence) != len(frame_states):
            print(f"\n⚠️ Número de frames diferente:")
            print(f"  Input: {len(frame_states)} frames")
            print(f"  Output: {len(sequence)} frames")
            
            if len(sequence) > len(frame_states):
                print(f"  📊 Frames extras: {len(sequence) - len(frame_states)}")
                for i in range(len(frame_states), len(sequence)):
                    extra_frame = sequence[i]
                    print(f"    Extra {i}: {extra_frame.get('char', '?')} ({extra_frame.get('ms', 0)}ms)")
        
        return abs(expected_total - actual_total) < 1.0  # Tolerância de 1ms
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_timing_precision()
    print(f"\n🏁 RESULTADO: {'✅ SUCESSO' if success else '❌ FALHOU'}")