#!/usr/bin/env python3
"""
Teste final otimizado - cenário realista sem frames extras
"""

import sys
import os

# Adiciona o diretório atual ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_optimized_scenario():
    """Teste final com cenário otimizado e realista"""
    
    print("🎯 TESTE FINAL OTIMIZADO")
    print("=" * 50)
    
    # Frase completa mas com timing mais realista
    sentence = "ESTE PROJETO DEMONSTRA ALINHAMENTO PERFEITO"
    words = sentence.split()
    
    # Cria frame_states mais realistas (sem excessos)
    frame_states = []
    
    for i, word in enumerate(words):
        # Pequena pausa entre palavras (apenas 1 frame)
        if i > 0:
            frame_states.append({
                'active_word': '',
                'ms': 33.33,
                'is_pause': True
            })
        
        # Palavra com duração proporcional ao tamanho
        word_frames = max(2, min(6, len(word)))  # Entre 2-6 frames por palavra
        
        for f in range(word_frames):
            frame_states.append({
                'active_word': word,
                'ms': 33.33,
                'is_pause': False
            })
    
    expected_total = sum(f['ms'] for f in frame_states)
    
    print(f"📝 Texto: {sentence}")
    print(f"🎬 Frames de entrada: {len(frame_states)}")
    print(f"⏱️ Duração esperada: {expected_total/1000:.3f}s")
    print(f"🔤 Palavras: {len(words)}")
    
    # Projeto mock
    mock_project = {
        'letter_map': {chr(i): f'{chr(i)}.png' for i in range(ord('A'), ord('Z')+1)},
        'special_tokens': {},
        'fallback_image': 'fallback.png',
        'pause_image': 'pause.png'
    }
    
    # Testa o alinhamento
    try:
        from app import build_text_driven_sequence_enhanced
        
        sequence = build_text_driven_sequence_enhanced(
            frame_states,
            sentence,
            mock_project
        )
        
        actual_total = sum(f['ms'] for f in sequence)
        letter_frames = [f for f in sequence if not f.get('is_pause')]
        pause_frames = [f for f in sequence if f.get('is_pause')]
        
        print(f"\n✅ RESULTADOS:")
        print(f"  🎥 Frames gerados: {len(sequence)}")
        print(f"  ⏱️ Duração final: {actual_total/1000:.3f}s")
        print(f"  📝 Frames de letras: {len(letter_frames)}")
        print(f"  ⏸️ Frames de pausas: {len(pause_frames)}")
        
        # Verifica precisão do timing
        timing_error = abs(expected_total - actual_total)
        print(f"  📊 Diferença de timing: {timing_error:.1f}ms")
        
        # Verifica cobertura de palavras
        words_in_sequence = set()
        for frame in letter_frames:
            if frame.get('word'):
                words_in_sequence.add(frame['word'])
        
        coverage_percent = len(words_in_sequence) / len(words) * 100
        print(f"  📈 Cobertura de palavras: {coverage_percent:.1f}%")
        
        # Verifica última palavra
        last_10_letters = letter_frames[-5:] if len(letter_frames) >= 5 else letter_frames
        print(f"\n🔍 ÚLTIMAS 5 LETRAS:")
        for i, frame in enumerate(last_10_letters):
            char = frame.get('char', '?')
            word = frame.get('word', '?')
            progress = frame.get('word_progress', 0)
            print(f"  {char} de '{word}' (progresso: {progress:.3f})")
        
        # Validação final
        timing_ok = timing_error < 10  # 10ms de tolerância
        coverage_ok = coverage_percent == 100.0
        frames_ok = len(sequence) == len(frame_states)  # Deve preservar número de frames
        
        print(f"\n🏆 VALIDAÇÃO FINAL:")
        print(f"  ⏱️ Timing preciso: {'✅' if timing_ok else '❌'} ({timing_error:.1f}ms)")
        print(f"  📊 Cobertura completa: {'✅' if coverage_ok else '❌'} ({coverage_percent:.1f}%)")
        print(f"  🎬 Frames preservados: {'✅' if frames_ok else '❌'} ({len(sequence)}/{len(frame_states)})")
        
        # Testa palavra específica que tinha problema
        perfeito_frames = [f for f in letter_frames if f.get('word') == 'PERFEITO']
        if perfeito_frames:
            chars_shown = [f.get('char') for f in perfeito_frames]
            print(f"\n🎯 Palavra 'PERFEITO': {'-'.join(chars_shown)}")
            print(f"  Caracteres únicos: {len(set(chars_shown))}/8 ({len(set(chars_shown))/8*100:.1f}%)")
        
        success = timing_ok and coverage_ok and frames_ok
        
        if success:
            print(f"\n🎉 TODAS AS MELHORIAS FUNCIONANDO PERFEITAMENTE!")
            print(f"✅ Problema dos 40 segundos: RESOLVIDO")
            print(f"✅ Truncamento de palavras: CORRIGIDO")
            print(f"✅ Timing preciso: MANTIDO")
            print(f"✅ Alinhamento 100%: ALCANÇADO")
        else:
            print(f"\n⚠️ Algumas melhorias precisam de ajustes finais")
            
        return success
        
    except Exception as e:
        print(f"❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_optimized_scenario()
    print(f"\n🚀 STATUS FINAL: {'🎯 100% SUCESSO!' if success else '⚙️ Ajustes necessários'}")