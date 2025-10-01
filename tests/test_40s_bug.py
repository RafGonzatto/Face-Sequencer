#!/usr/bin/env python3
"""
Teste específico para debug do problema de dessincronização aos 40 segundos
"""

import sys
import os

# Adiciona o diretório atual ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_long_alignment_scenario():
    """Simula um cenário longo com problema aos 40 segundos"""
    
    # Simula frame_states para ~60 segundos (1800 frames @ 30fps)
    mock_frame_states = []
    
    # Primeiros 40 segundos - funcionam bem
    words_first_40s = ["ESTE", "É", "UM", "TESTE", "MUITO", "LONGO", "PARA", "VERIFICAR", "A", "QUALIDADE"]
    
    frame_count = 0
    for word in words_first_40s:
        # Pausa antes da palavra
        mock_frame_states.append({
            'active_word': '', 
            'ms': 33.33, 
            'is_pause': True
        })
        frame_count += 1
        
        # Frames da palavra (3-5 frames por palavra)
        word_frames = max(3, len(word))
        for i in range(word_frames):
            mock_frame_states.append({
                'active_word': word,
                'ms': 33.33,
                'is_pause': False
            })
            frame_count += 1
    
    print(f"⏱️ Primeiros 40s simulados: {frame_count} frames ({frame_count * 33.33 / 1000:.1f}s)")
    
    # Segundos 40-60 - onde o problema acontece  
    words_problem_area = ["DO", "ALINHAMENTO", "DE", "AUDIO", "E", "TEXTO", "NO", "PROJETO"]
    
    for word in words_problem_area:
        # Pausa
        mock_frame_states.append({
            'active_word': '', 
            'ms': 33.33, 
            'is_pause': True
        })
        frame_count += 1
        
        # Palavra com duração variável (simula problema)
        word_frames = max(2, len(word) // 2)  # Menos frames = problema
        for i in range(word_frames):
            mock_frame_states.append({
                'active_word': word,
                'ms': 33.33 + (i * 5),  # Duração variável = problema
                'is_pause': False
            })
            frame_count += 1
    
    print(f"⏱️ Total simulado: {frame_count} frames ({frame_count * 33.33 / 1000:.1f}s)")
    
    # Mock do projeto
    mock_project = {
        'letter_map': {
            'A': 'A.png', 'B': 'B.png', 'C': 'C.png', 'D': 'D.png', 'E': 'E.png',
            'F': 'F.png', 'G': 'G.png', 'H': 'H.png', 'I': 'I.png', 'J': 'J.png',
            'K': 'K.png', 'L': 'L.png', 'M': 'M.png', 'N': 'N.png', 'O': 'O.png',
            'P': 'P.png', 'Q': 'Q.png', 'R': 'R.png', 'S': 'S.png', 'T': 'T.png',
            'U': 'U.png', 'V': 'V.png', 'W': 'W.png', 'X': 'X.png', 'Y': 'Y.png', 'Z': 'Z.png'
        },
        'special_tokens': {},
        'fallback_image': 'fallback.png',
        'pause_image': 'pause.png'
    }
    
    text = " ".join(words_first_40s + words_problem_area)
    
    print(f"\n🧪 Testando cenário longo:")
    print(f"📝 Texto: {text}")
    print(f"🎬 Frame states: {len(mock_frame_states)} frames")
    
    # Importa e testa a função
    try:
        from app import build_text_driven_sequence_enhanced
        
        sequence = build_text_driven_sequence_enhanced(
            mock_frame_states,
            text,
            mock_project
        )
        
        print(f"\n✅ Sequência gerada: {len(sequence)} frames")
        
        # Análise detalhada
        total_duration_ms = sum(f['ms'] for f in sequence)
        letter_frames = [f for f in sequence if not f.get('is_pause')]
        pause_frames = [f for f in sequence if f.get('is_pause')]
        
        print(f"📊 Estatísticas:")
        print(f"  - Duração total: {total_duration_ms/1000:.1f}s")
        print(f"  - Frames de letras: {len(letter_frames)}")
        print(f"  - Frames de pausas: {len(pause_frames)}")
        
        # Verifica últimas palavras
        last_10_letter_frames = [f for f in sequence if not f.get('is_pause')][-10:]
        print(f"\n🔍 Últimas 10 letras:")
        for i, frame in enumerate(last_10_letter_frames):
            char = frame.get('char', '?')
            word = frame.get('word', 'unknown')
            progress = frame.get('word_progress', 0)
            print(f"  {len(letter_frames)-10+i:3d}: '{char}' palavra='{word}' progresso={progress:.3f}")
        
        # Verifica se última palavra foi completa
        last_words = set()
        for frame in sequence[-20:]:  # Últimos 20 frames
            if not frame.get('is_pause') and frame.get('word'):
                last_words.add(frame['word'])
        
        print(f"\n🎯 Últimas palavras detectadas: {list(last_words)}")
        
        expected_last_word = words_problem_area[-1]
        if expected_last_word in last_words:
            print(f"✅ Última palavra '{expected_last_word}' foi processada")
        else:
            print(f"❌ Última palavra '{expected_last_word}' pode ter sido cortada!")
            
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_long_alignment_scenario()