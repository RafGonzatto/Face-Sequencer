#!/usr/bin/env python3
"""
Debug específico da tokenização de palavras
"""

import sys
import os

# Adiciona o diretório atual ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def debug_word_tokenization():
    """Debug da tokenização da palavra PROJETO"""
    
    from app import tokenize_word_enhanced
    
    mock_project = {
        'letter_map': {
            'P': 'P.png', 'R': 'R.png', 'O': 'O.png', 'J': 'J.png', 
            'E': 'E.png', 'T': 'T.png'
        },
        'special_tokens': {},
        'fallback_image': 'fallback.png'
    }
    
    word = "PROJETO"
    tokens = tokenize_word_enhanced(
        word, 
        mock_project.get('special_tokens', {}),
        is_word_start=True,
        project=mock_project
    )
    
    print(f"🔍 Debug tokenização da palavra '{word}':")
    print(f"Tokens gerados: {len(tokens)}")
    for i, token in enumerate(tokens):
        print(f"  {i}: '{token['token']}' -> {token['img']}")
    
    # Simula 3 frames para a palavra PROJETO
    frames_in_word = 3
    
    print(f"\n🎬 Simulando {frames_in_word} frames para '{word}':")
    
    for frame_idx in range(frames_in_word):
        frames_elapsed = frame_idx
        
        # Lógica atual (problemática)
        segment_size = frames_in_word / len(tokens)
        token_idx_old = min(int(frames_elapsed / segment_size), len(tokens) - 1)
        
        # Nova lógica melhorada (igual à implementada no app.py)
        if len(tokens) == 1:
            token_idx_new = 0
        elif frames_in_word >= len(tokens):
            # Enough frames - distribute evenly with proper spacing
            token_idx_new = min(int((frames_elapsed * (len(tokens) - 1)) / (frames_in_word - 1)), len(tokens) - 1)
        else:
            # Fewer frames than tokens - prioritize key tokens
            if frames_in_word <= 1:
                token_idx_new = 0  # Only first token
            elif frames_in_word == 2:
                token_idx_new = 0 if frames_elapsed == 0 else len(tokens) - 1  # First and last
            elif frames_in_word == 3:
                # Show: first, middle, last
                if frames_elapsed == 0:
                    token_idx_new = 0
                elif frames_elapsed == 1:
                    token_idx_new = len(tokens) // 2
                else:
                    token_idx_new = len(tokens) - 1
            else:
                # General case: smart distribution
                progress = frames_elapsed / (frames_in_word - 1)
                token_idx_new = min(int(progress * (len(tokens) - 1)), len(tokens) - 1)
        
        print(f"  Frame {frame_idx}: elapsed={frames_elapsed}/{frames_in_word}")
        print(f"    Lógica atual: token_idx={token_idx_old} -> '{tokens[token_idx_old]['token']}'")
        print(f"    Lógica nova:  token_idx={token_idx_new} -> '{tokens[token_idx_new]['token']}'")

def debug_word_boundaries():
    """Debug dos word boundaries"""
    
    # Simula frame_states para PROJETO com 3 frames
    mock_frame_states = [
        {'active_word': 'PROJETO', 'ms': 33.33, 'is_pause': False},  # Frame 0
        {'active_word': 'PROJETO', 'ms': 33.33, 'is_pause': False},  # Frame 1  
        {'active_word': 'PROJETO', 'ms': 33.33, 'is_pause': False},  # Frame 2
    ]
    
    print(f"\n🎯 Debug word boundaries para PROJETO:")
    
    # Simula a lógica de word boundaries
    word_boundaries = []
    current_word_start_frame = None
    current_word_start_time = None
    current_word = ""
    
    # Calculate cumulative timestamps
    cumulative_time = 0.0
    frame_timestamps = []
    
    for i, state in enumerate(mock_frame_states):
        frame_timestamps.append(cumulative_time)
        ms = state.get('ms', 33.33)
        cumulative_time += ms / 1000.0
    
    # Process word boundaries
    for i, state in enumerate(mock_frame_states):
        active_word = state.get('active_word', '')
        current_timestamp = frame_timestamps[i]
        
        # Detect word start
        if active_word and not current_word:
            current_word_start_frame = i
            current_word_start_time = current_timestamp
            current_word = active_word
            
        # Detect word end (change or end of frames)
        elif current_word and (not active_word or active_word != current_word):
            if current_word_start_frame is not None:
                word_boundaries.append({
                    'word': current_word,
                    'start': current_word_start_time,
                    'end': current_timestamp,
                    'start_frame': current_word_start_frame,
                    'end_frame': i - 1
                })
            
            if active_word:
                current_word_start_frame = i
                current_word_start_time = current_timestamp
                current_word = active_word
            else:
                current_word = ""
                current_word_start_frame = None
                current_word_start_time = None
    
    # Add last word
    if current_word and current_word_start_frame is not None:
        final_timestamp = cumulative_time
        word_boundaries.append({
            'word': current_word,
            'start': current_word_start_time,
            'end': final_timestamp,
            'start_frame': current_word_start_frame,
            'end_frame': len(mock_frame_states) - 1
        })
    
    if word_boundaries:
        boundary = word_boundaries[0]
        print(f"Word boundary: '{boundary['word']}'")
        print(f"  Frames: {boundary['start_frame']} - {boundary['end_frame']}")
        
        frames_in_word = boundary['end_frame'] - boundary['start_frame'] + 1
        print(f"  Total frames in word: {frames_in_word}")
        
        # Simula progressão frame por frame
        for i in range(len(mock_frame_states)):
            if boundary['start_frame'] <= i <= boundary['end_frame']:
                frames_elapsed = i - boundary['start_frame']
                word_progress = frames_elapsed / frames_in_word if frames_in_word > 1 else 0
                print(f"    Frame {i}: elapsed={frames_elapsed} progress={word_progress:.3f}")

if __name__ == '__main__':
    debug_word_tokenization()
    debug_word_boundaries()