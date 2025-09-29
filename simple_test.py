#!/usr/bin/env python3
"""
Teste rápido para o problema de truncamento
"""

def test_simple():
    print("🧪 Teste simples de truncamento")
    
    # Importar função
    from app import build_text_driven_sequence_enhanced
    
    # Criar dados de teste simples
    frame_states = []
    for i in range(100):  # 100 frames = ~3.3s
        frame_states.append({
            'ms': 33.33,
            'active_word': 'TESTE' if i < 50 else 'PALAVRA',
            'is_pause': False
        })
    
    project = {
        'letter_map': {'T': 'test.jpg', 'P': 'palavra.jpg'},
        'fallback_image': 'fallback.jpg'
    }
    
    text = "TESTE PALAVRA"
    
    print(f"📊 Frame states: {len(frame_states)}")
    
    # Executar função
    sequence = build_text_driven_sequence_enhanced(frame_states, text, project)
    
    print(f"📊 Sequence: {len(sequence)}")
    print(f"📊 Diferença: {len(frame_states) - len(sequence)} frames")
    
    if len(sequence) >= len(frame_states) * 0.9:  # 90% ou mais
        print("✅ PASSOU: Sem truncamento significativo")
        return True
    else:
        print("❌ FALHOU: Truncamento detectado")
        return False

if __name__ == "__main__":
    test_simple()