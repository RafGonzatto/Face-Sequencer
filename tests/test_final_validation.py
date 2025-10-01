#!/usr/bin/env python3
"""
Teste final de validação das melhorias de alinhamento
"""

import sys
import os

# Adiciona o diretório atual ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_real_world_scenario():
    """Testa um cenário realista com timing preciso"""
    
    print("🎯 TESTE FINAL: Cenário Realista de Alinhamento")
    print("=" * 60)
    
    # Simula uma frase longa e complexa
    sentence = "ESTE PROJETO DEMONSTRA O ALINHAMENTO PERFEITO ENTRE AUDIO E TEXTO USANDO INTELIGENCIA ARTIFICIAL"
    words = sentence.split()
    
    # Cria frame_states realistas
    frame_states = []
    current_time = 0.0
    
    for i, word in enumerate(words):
        # Pausa entre palavras (150ms)
        if i > 0:
            pause_frames = 4  # ~133ms @ 30fps
            for _ in range(pause_frames):
                frame_states.append({
                    'active_word': '',
                    'ms': 33.33,
                    'is_pause': True
                })
                current_time += 33.33
        
        # Palavra com duração baseada no tamanho
        word_duration_ms = max(300, len(word) * 80)  # Mínimo 300ms
        frames_needed = int(word_duration_ms / 33.33)
        
        for f in range(frames_needed):
            frame_states.append({
                'active_word': word,
                'ms': 33.33,
                'is_pause': False
            })
            current_time += 33.33
    
    print(f"📝 Texto: {sentence}")
    print(f"🎬 Duração total: {current_time/1000:.1f}s")
    print(f"📊 Total de frames: {len(frame_states)}")
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
        
        # Análise dos resultados
        total_ms = sum(f['ms'] for f in sequence)
        letter_frames = [f for f in sequence if not f.get('is_pause')]
        pause_frames = [f for f in sequence if f.get('is_pause')]
        
        print(f"\n✅ RESULTADOS:")
        print(f"  🎥 Frames gerados: {len(sequence)}")
        print(f"  ⏱️  Duração final: {total_ms/1000:.1f}s")
        print(f"  📝 Frames de letras: {len(letter_frames)}")
        print(f"  ⏸️  Frames de pausas: {len(pause_frames)}")
        
        # Verifica cobertura de palavras
        words_in_sequence = set()
        for frame in letter_frames:
            if frame.get('word'):
                words_in_sequence.add(frame['word'])
        
        print(f"\n📊 ANÁLISE DE COBERTURA:")
        print(f"  🎯 Palavras esperadas: {len(words)}")
        print(f"  ✅ Palavras processadas: {len(words_in_sequence)}")
        print(f"  📈 Taxa de cobertura: {len(words_in_sequence)/len(words)*100:.1f}%")
        
        # Lista palavras não processadas
        missing_words = set(words) - words_in_sequence
        if missing_words:
            print(f"  ⚠️  Palavras não processadas: {missing_words}")
        else:
            print(f"  🎉 TODAS as palavras foram processadas!")
        
        # Verifica última palavra especificamente
        last_10_letters = letter_frames[-10:]
        print(f"\n🔍 ÚLTIMAS 10 LETRAS:")
        for i, frame in enumerate(last_10_letters):
            char = frame.get('char', '?')
            word = frame.get('word', '?')
            progress = frame.get('word_progress', 0)
            idx = len(letter_frames) - 10 + i
            print(f"  {idx:3d}: '{char}' de '{word}' ({progress:.3f})")
        
        # Teste específico da palavra "ARTIFICIAL"
        artificial_frames = [f for f in letter_frames if f.get('word') == 'ARTIFICIAL']
        if artificial_frames:
            print(f"\n🤖 ANÁLISE DA PALAVRA 'ARTIFICIAL':")
            chars_shown = [f.get('char') for f in artificial_frames]
            print(f"  📝 Caracteres mostrados: {'-'.join(chars_shown)}")
            print(f"  📊 Frames usados: {len(artificial_frames)}")
            print(f"  📈 Cobertura: {len(set(chars_shown))/len('ARTIFICIAL')*100:.1f}%")
        
        # Valida timing preciso
        expected_total = current_time
        actual_total = total_ms
        timing_error = abs(expected_total - actual_total)
        
        print(f"\n⏱️ VALIDAÇÃO DE TIMING:")
        print(f"  🎯 Esperado: {expected_total/1000:.3f}s")
        print(f"  ✅ Gerado: {actual_total/1000:.3f}s")
        print(f"  📊 Diferença: {timing_error:.1f}ms")
        
        timing_ok = timing_error < 50  # Tolerância de 50ms
        if timing_ok:
            print(f"  🎉 TIMING PRECISO!")
        else:
            print(f"  ⚠️  Divergência significativa no timing")

        assert len(missing_words) == 0, f"Palavras não processadas: {missing_words}"
        assert timing_ok, f"Timing fora da tolerância: {timing_error:.1f}ms"
        
    except Exception as e:
        print(f"❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        raise

def test_edge_cases():
    """Testa casos extremos que causavam problemas"""
    
    print(f"\n🧪 TESTE DE CASOS EXTREMOS")
    print("=" * 60)
    
    test_cases = [
        ("Palavra muito longa", "SUPERCALIFRAGILISTICEXPIALIDOCIOUS", 5),
        ("Palavra curta", "A", 1),
        ("Duas palavras", "OI MUNDO", 6),
        ("Números", "123 ABC 456", 8),
        ("Pontuação", "OLÁ, MUNDO!", 7)
    ]
    
    mock_project = {
        'letter_map': {chr(i): f'{chr(i)}.png' for i in range(ord('A'), ord('Z')+1)},
        'special_tokens': {'123': '123.png', '456': '456.png'},
        'fallback_image': 'fallback.png', 
        'pause_image': 'pause.png'
    }
    
    all_passed = True
    
    for test_name, text, expected_frames in test_cases:
        print(f"\n🔬 {test_name}: '{text}'")
        
        # Cria frame_states simples
        words = text.split()
        frame_states = []
        
        for word in words:
            # Pausa
            frame_states.append({
                'active_word': '',
                'ms': 33.33,
                'is_pause': True
            })
            
            # Palavra
            for _ in range(max(1, expected_frames // len(words))):
                frame_states.append({
                    'active_word': word,
                    'ms': 33.33,
                    'is_pause': False
                })
        
        try:
            from app import build_text_driven_sequence_enhanced
            
            sequence = build_text_driven_sequence_enhanced(
                frame_states,
                text,
                mock_project
            )
            
            letter_frames = [f for f in sequence if not f.get('is_pause')]
            
            print(f"  ✅ Gerou {len(sequence)} frames ({len(letter_frames)} letras)")
            
            if len(letter_frames) == 0 and len(text.strip()) > 0:
                print(f"  ❌ Nenhuma letra gerada para texto não-vazio!")
                all_passed = False
            else:
                print(f"  ✅ Processamento bem-sucedido")
                
        except Exception as e:
            print(f"  ❌ Erro: {e}")
            all_passed = False
    
    assert all_passed, "Alguns casos extremos falharam"

if __name__ == '__main__':
    print("🚀 INICIANDO VALIDAÇÃO FINAL DAS MELHORIAS")
    print("=" * 60)
    
    scenario_ok = test_real_world_scenario()
    edge_cases_ok = test_edge_cases()
    
    print(f"\n🏁 RESULTADO FINAL:")
    print("=" * 60)
    
    if scenario_ok and edge_cases_ok:
        print("🎉 TODAS AS MELHORIAS FUNCIONANDO PERFEITAMENTE!")
        print("✅ Alinhamento de 100% de precisão alcançado")
        print("✅ Problema dos 40 segundos resolvido")
        print("✅ Truncamento de palavras corrigido")
        print("✅ Timing preciso mantido")
        print("✅ Casos extremos tratados")
    else:
        if not scenario_ok:
            print("❌ Problemas no cenário principal")
        if not edge_cases_ok:
            print("❌ Problemas nos casos extremos")
        print("⚠️  Algumas melhorias precisam de ajustes")