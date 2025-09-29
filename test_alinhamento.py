#!/usr/bin/env python3
"""
Teste específico para palavra longa "ALINHAMENTO"
"""

import sys
import os

# Adiciona o diretório atual ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_alinhamento_word():
    """Testa especificamente a palavra ALINHAMENTO"""
    
    from app import tokenize_word_enhanced
    
    mock_project = {
        'letter_map': {
            'A': 'A.png', 'L': 'L.png', 'I': 'I.png', 'N': 'N.png', 'H': 'H.png',
            'M': 'M.png', 'E': 'E.png', 'T': 'T.png', 'O': 'O.png'
        },
        'special_tokens': {},
        'fallback_image': 'fallback.png'
    }
    
    word = "ALINHAMENTO"
    tokens = tokenize_word_enhanced(
        word,
        mock_project.get('special_tokens', {}),
        is_word_start=True,
        project=mock_project
    )
    
    print(f"🔍 Análise detalhada da palavra '{word}':")
    print(f"Tokens: {[t['token'] for t in tokens]} ({len(tokens)} total)")
    
    # Identifica vogais e consoantes importantes
    vowels = set('AEIOUÁÉÍÓÚÃÕ')
    important_consonants = set('BLMNPRST')
    
    print(f"\nAnálise de caracteres:")
    for i, token in enumerate(tokens):
        char = token['token'].upper()
        char_type = "VOGAL" if char in vowels else "CONS.IMPORTANTE" if char in important_consonants else "OUTRA"
        print(f"  {i:2d}: '{char}' -> {char_type}")
    
    # Simula a lógica de seleção para 5 frames
    frames_in_word = 5
    print(f"\nSimulação para {frames_in_word} frames:")
    
    # Nova lógica implementada
    if len(tokens) > frames_in_word * 1.5:  # 11 > 5*1.5 = True
        print("Usando nova lógica para palavra longa...")
        
        # Score each token by importance
        token_scores = []
        for i, token in enumerate(tokens):
            char = token['token'].upper()
            score = 0
            
            # Base importance
            if char in vowels:
                score += 3  # Vowels are very important
            elif char in important_consonants:
                score += 2  # Important consonants
            else:
                score += 1  # Other consonants
            
            # Position bonus - first and last are more important
            if i == 0 or i == len(tokens) - 1:
                score += 2
            elif i <= 2 or i >= len(tokens) - 3:
                score += 1
            
            token_scores.append((i, score, char))
        
        print(f"\nPontuação dos tokens:")
        for idx, score, char in token_scores:
            print(f"  {idx:2d}: '{char}' -> {score} pontos")
        
        # Sort by score (descending) and select top tokens
        token_scores.sort(key=lambda x: (-x[1], x[0]))  # By score, then position
        selected_indices = [idx for idx, score, char in token_scores[:frames_in_word]]
        selected_indices.sort()  # Keep chronological order
        
        print(f"\nÍndices selecionados (top {frames_in_word}): {selected_indices}")
        print(f"Caracteres selecionados: {[tokens[i]['token'] for i in selected_indices]}")
        
        # Simula distribuição nos frames
        for frame_idx in range(frames_in_word):
            progress = frame_idx / (frames_in_word - 1) if frames_in_word > 1 else 0
            idx_position = min(int(progress * (len(selected_indices) - 1)), len(selected_indices) - 1)
            token_idx = selected_indices[idx_position]
            
            char = tokens[token_idx]['token']
            print(f"  Frame {frame_idx}: progress={progress:.3f} -> pos={idx_position} -> idx={token_idx} -> '{char}'")

if __name__ == '__main__':
    test_alinhamento_word()