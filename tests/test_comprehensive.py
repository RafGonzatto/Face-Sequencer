#!/usr/bin/env python3
"""
Teste abrangente para validar as correções do alinhamento
"""

import sys
import os

# Adiciona o diretório atual ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_various_word_lengths():
    """Testa palavras de diferentes tamanhos com diferentes números de frames"""
    
    from app import build_text_driven_sequence_enhanced, tokenize_word_enhanced
    
    # Mock projeto
    mock_project = {
        'letter_map': {
            'A': 'A.png', 'B': 'B.png', 'C': 'C.png', 'D': 'D.png', 'E': 'E.png',
            'F': 'F.png', 'G': 'G.png', 'H': 'H.png', 'I': 'I.png', 'J': 'J.png',
            'L': 'L.png', 'M': 'M.png', 'N': 'N.png', 'O': 'O.png', 'P': 'P.png',
            'R': 'R.png', 'S': 'S.png', 'T': 'T.png', 'U': 'U.png', 'V': 'V.png'
        },
        'special_tokens': {},
        'fallback_image': 'fallback.png',
        'pause_image': 'pause.png'
    }
    
    # Testa diferentes cenários
    test_cases = [
        # (palavra, num_frames, descrição)
        ("EU", 2, "Palavra curta com frames suficientes"),
        ("CASA", 3, "Palavra média com poucos frames"),
        ("PROJETO", 3, "Palavra longa com poucos frames"),
        ("DESENVOLVIMENTO", 8, "Palavra muito longa com frames adequados"),
        ("A", 1, "Palavra de 1 letra"),
        ("ALINHAMENTO", 5, "Palavra longa com frames médios")
    ]
    
    print("🧪 Teste de diferentes tamanhos de palavras:")
    print("="*60)
    
    for word, num_frames, description in test_cases:
        print(f"\n📝 {description}: '{word}' com {num_frames} frames")
        
        # Tokeniza a palavra
        tokens = tokenize_word_enhanced(
            word,
            mock_project.get('special_tokens', {}),
            is_word_start=True,
            project=mock_project
        )
        
        print(f"   Tokens: {[t['token'] for t in tokens]} ({len(tokens)} total)")
        
        # Simula frames
        mock_frame_states = []
        for i in range(num_frames):
            mock_frame_states.append({
                'active_word': word,
                'ms': 33.33,
                'is_pause': False
            })
        
        # Testa o alinhamento
        sequence = build_text_driven_sequence_enhanced(
            mock_frame_states,
            word,
            mock_project
        )
        
        # Analisa resultado
        letter_frames = [f for f in sequence if not f.get('is_pause')]
        
        print(f"   Resultado: ", end="")
        for i, frame in enumerate(letter_frames):
            char = frame.get('char', '?')
            progress = frame.get('word_progress', 0)
            print(f"{char}({progress:.2f})", end=" ")
        
        print(f"")
        
        # Verifica qualidade
        unique_chars = set(f.get('char') for f in letter_frames)
        coverage = len(unique_chars) / len(set(word)) if word else 0
        
        if coverage >= 0.5:  # Pelo menos 50% das letras únicas mostradas
            print(f"   ✅ Boa cobertura: {coverage:.1%} das letras")
        else:
            print(f"   ⚠️  Cobertura baixa: {coverage:.1%} das letras")

def test_timing_accuracy():
    """Testa a precisão do timing com durações variáveis"""
    
    from app import build_text_driven_sequence_enhanced
    
    mock_project = {
        'letter_map': {chr(i): f'{chr(i)}.png' for i in range(ord('A'), ord('Z')+1)},
        'special_tokens': {},
        'fallback_image': 'fallback.png',
        'pause_image': 'pause.png'
    }
    
    print("\n🕒 Teste de precisão de timing:")
    print("="*60)
    
    # Simula um cenário com durações variáveis (comum em áudio real)
    words = ["OLÁ", "MUNDO", "TESTE"]
    frame_durations = [30.0, 35.0, 40.0, 25.0, 50.0, 33.33, 28.0]  # ms variáveis
    
    mock_frame_states = []
    frame_idx = 0
    
    for word in words:
        # Pausa antes da palavra
        mock_frame_states.append({
            'active_word': '',
            'ms': frame_durations[frame_idx % len(frame_durations)],
            'is_pause': True
        })
        frame_idx += 1
        
        # Frames da palavra com durações variáveis
        word_frame_count = max(2, len(word) // 2)
        for i in range(word_frame_count):
            mock_frame_states.append({
                'active_word': word,
                'ms': frame_durations[frame_idx % len(frame_durations)],
                'is_pause': False
            })
            frame_idx += 1
    
    text = " ".join(words)
    
    sequence = build_text_driven_sequence_enhanced(
        mock_frame_states,
        text,
        mock_project
    )
    
    # Análise de timing
    total_duration = sum(f['ms'] for f in sequence)
    expected_duration = sum(s['ms'] for s in mock_frame_states)
    
    print(f"Duração esperada: {expected_duration:.1f}ms")
    print(f"Duração gerada: {total_duration:.1f}ms")
    print(f"Diferença: {abs(total_duration - expected_duration):.1f}ms")
    
    if abs(total_duration - expected_duration) < 1.0:
        print("✅ Timing preciso!")
    else:
        print("⚠️  Diferença de timing detectada")
    
    # Analisa progressão temporal
    cumulative_time = 0
    print(f"\nProgressão temporal:")
    for i, frame in enumerate(sequence[:10]):  # Primeiros 10 frames
        char = frame.get('char', ' ')
        ms = frame['ms']
        cumulative_time += ms
        word = frame.get('word', '')
        is_pause = frame.get('is_pause', False)
        
        frame_type = "PAUSE" if is_pause else "LETTER"
        print(f"  {i:2d}: {frame_type:6s} '{char}' +{ms:5.1f}ms = {cumulative_time:6.1f}ms total | {word}")

def test_edge_cases():
    """Testa casos extremos que podem causar bugs"""
    
    from app import build_text_driven_sequence_enhanced
    
    mock_project = {
        'letter_map': {'A': 'A.png', 'B': 'B.png'},
        'special_tokens': {},
        'fallback_image': 'fallback.png',
        'pause_image': 'pause.png'
    }
    
    print("\n⚠️  Teste de casos extremos:")
    print("="*60)
    
    edge_cases = [
        # (descrição, frame_states, text)
        ("Palavra sem frames", [], "TESTE"),
        ("Frame sem active_word", [{'active_word': '', 'ms': 33.33, 'is_pause': False}], ""),
        ("Última palavra incompleta", [
            {'active_word': 'TESTE', 'ms': 33.33, 'is_pause': False},
            {'active_word': 'TESTE', 'ms': 33.33, 'is_pause': False},
            # Falta o final da palavra
        ], "TESTE COMPLETO"),
        ("Duração zero", [{'active_word': 'A', 'ms': 0, 'is_pause': False}], "A"),
    ]
    
    for description, frame_states, text in edge_cases:
        print(f"\n🔍 {description}:")
        
        try:
            sequence = build_text_driven_sequence_enhanced(
                frame_states,
                text,
                mock_project
            )
            
            print(f"   ✅ Processado: {len(sequence)} frames gerados")
            
            if sequence:
                total_ms = sum(f['ms'] for f in sequence)
                print(f"   Duração total: {total_ms:.1f}ms")
                
        except Exception as e:
            print(f"   ❌ Erro: {e}")

if __name__ == '__main__':
    test_various_word_lengths()
    test_timing_accuracy()
    test_edge_cases()