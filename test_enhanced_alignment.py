#!/usr/bin/env python3
"""
Teste da implementação enhanced alignment
"""

import sys
import os

# Adiciona o diretório atual ao path para importar os módulos
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Mock do app_state para teste
mock_app_state = {
    'current_project': {
        'letter_map': {
            'A': 'path/to/A.png',
            'B': 'path/to/B.png',
            'C': 'path/to/C.png',
            'E': 'path/to/E.png',
            'L': 'path/to/L.png',
            'O': 'path/to/O.png'
        },
        'special_tokens': {
            'CH': 'path/to/CH.png',
            'Aa': 'path/to/Aa.png',  # Vogal inicial A
            'Ee': 'path/to/Ee.png'   # Vogal inicial E
        },
        'fallback_image': 'path/to/fallback.png',
        'pause_image': 'path/to/pause.png',
        'sequence': []
    }
}

# Mock frame_states simulando alinhamento de áudio
mock_frame_states = [
    {'active_word': '', 'ms': 33.33, 'is_pause': True},  # Pausa inicial
    {'active_word': 'HELLO', 'ms': 33.33, 'is_pause': False},  # Frame 1 de HELLO
    {'active_word': 'HELLO', 'ms': 33.33, 'is_pause': False},  # Frame 2 de HELLO
    {'active_word': 'HELLO', 'ms': 33.33, 'is_pause': False},  # Frame 3 de HELLO
    {'active_word': '', 'ms': 33.33, 'is_pause': True},        # Pausa entre palavras
    {'active_word': 'WORLD', 'ms': 33.33, 'is_pause': False}, # Frame 1 de WORLD
    {'active_word': 'WORLD', 'ms': 33.33, 'is_pause': False}, # Frame 2 de WORLD
    {'active_word': 'WORLD', 'ms': 33.33, 'is_pause': False}, # Frame 3 de WORLD
    {'active_word': '', 'ms': 33.33, 'is_pause': True},       # Pausa final
]

def test_enhanced_sequence():
    """Testa a nova função build_text_driven_sequence_enhanced"""
    
    # Importa as funções necessárias
    from app import build_text_driven_sequence_enhanced, tokenize_word_enhanced
    
    text = "HELLO WORLD"
    
    print("🧪 Testando build_text_driven_sequence_enhanced")
    print(f"📝 Texto: '{text}'")
    print(f"🎬 Frame states: {len(mock_frame_states)} frames")
    
    # Testa a função
    sequence = build_text_driven_sequence_enhanced(
        mock_frame_states, 
        text, 
        mock_app_state['current_project']
    )
    
    print(f"\n✅ Resultado: {len(sequence)} frames gerados")
    
    for i, frame in enumerate(sequence):
        frame_type = "PAUSE" if frame.get('is_pause') else "LETRA"
        char = frame.get('char', '?')
        ms = frame.get('ms', 0)
        word = frame.get('word', '')
        progress = frame.get('word_progress', 0)
        
        if frame.get('is_pause'):
            print(f"  {i:2d}: {frame_type:5s} '{char}' ({ms:4.1f}ms)")
        else:
            print(f"  {i:2d}: {frame_type:5s} '{char}' ({ms:4.1f}ms) - palavra:'{word}' progresso:{progress:.2f}")
    
    print(f"\n📊 Estatísticas:")
    total_ms = sum(f['ms'] for f in sequence)
    letter_frames = [f for f in sequence if not f.get('is_pause')]
    pause_frames = [f for f in sequence if f.get('is_pause')]
    
    print(f"  - Total: {total_ms:.1f}ms ({len(sequence)} frames)")
    print(f"  - Letras: {len(letter_frames)} frames")
    print(f"  - Pausas: {len(pause_frames)} frames")

def test_tokenizer():
    """Testa a função tokenize_word_enhanced"""
    
    from app import tokenize_word_enhanced
    
    print("\n🧪 Testando tokenize_word_enhanced")
    
    test_words = ["HELLO", "CHAVE", "ÁGUA"]
    
    for word in test_words:
        tokens = tokenize_word_enhanced(
            word, 
            mock_app_state['current_project']['special_tokens'],
            is_word_start=True,
            project=mock_app_state['current_project']
        )
        
        print(f"  '{word}' -> {[t['token'] for t in tokens]}")

if __name__ == '__main__':
    try:
        test_tokenizer()
        test_enhanced_sequence()
        print("\n✅ Todos os testes passaram!")
    except Exception as e:
        print(f"\n❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()