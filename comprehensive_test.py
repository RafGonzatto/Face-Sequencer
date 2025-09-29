#!/usr/bin/env python3
"""
Teste Abrangente do Sistema de Anti-Truncamento
===============================================

Testa diferentes cenários para garantir que o vídeo sempre 
mantenha a duração correta do áudio.
"""

import json
import random
from app import build_text_driven_sequence_enhanced

def create_test_frame_states(duration_seconds, text="Texto de teste"):
    """Cria frame_states sintéticos para teste"""
    fps = 30
    total_frames = int(duration_seconds * fps)
    
    # Simula palavra única ou múltiplas palavras
    words = text.split()
    frame_states = []
    
    frames_per_word = total_frames // len(words)
    
    for i, word in enumerate(words):
        start_frame = i * frames_per_word
        end_frame = start_frame + frames_per_word
        
        if i == len(words) - 1:  # Última palavra pega frames restantes
            end_frame = total_frames
        
        for frame_idx in range(start_frame, end_frame):
            frame_states.append({
                'active_word': word,  # Campo esperado pela função
                'start_time': frame_idx / fps,
                'end_time': (frame_idx + 1) / fps,
                'timestamp': frame_idx / fps
            })
    
    return frame_states

def create_test_text_words(text="Texto de teste"):
    """Cria text_words para teste"""
    words = text.split()
    text_words = []
    
    for i, word in enumerate(words):
        text_words.append({
            'word': word,
            'start': i * 0.5,  # 500ms por palavra
            'end': (i + 1) * 0.5,
            'score': 0.95
        })
    
    return text_words

def create_test_tokens(text="Texto de teste"):
    """Cria tokens para teste"""
    tokens = []
    for char in text.replace(" ", ""):
        tokens.append({
            'token': char,
            'img': f"frame_{char}.jpg"
        })
    
    return tokens

def run_test_scenario(name, duration_seconds, text="Texto de teste complexo"):
    """Executa um cenário de teste específico"""
    print(f"\n{'='*60}")
    print(f"🧪 TESTE: {name}")
    print(f"   Duração: {duration_seconds}s")
    print(f"   Texto: '{text}'")
    print(f"{'='*60}")
    
    # Criar dados de teste
    frame_states = create_test_frame_states(duration_seconds, text)
    text_words = create_test_text_words(text)
    
    expected_frames = len(frame_states)
    
    print(f"📊 Frame states esperados: {expected_frames}")
    print(f"📊 Palavras no texto: {len(text_words)}")
    
    # Criar projeto mock para a função
    project = {
        'id': 'test_project',
        'tokens': create_test_tokens(text),
        'fallback_img': 'fallback.jpg'
    }
    
    try:
        # Executar função com assinatura correta (text deve ser string, não lista)
        sequence = build_text_driven_sequence_enhanced(
            frame_states, text, project
        )
        
        actual_frames = len(sequence)
        difference = abs(expected_frames - actual_frames)
        percentage_diff = (difference / expected_frames) * 100 if expected_frames > 0 else 0
        
        print(f"📊 Sequence gerada: {actual_frames} frames")
        print(f"📊 Diferença: {difference} frames ({percentage_diff:.2f}%)")
        
        # Validação
        if difference <= 1:  # Tolerância de 1 frame (33ms a 30fps)
            print(f"✅ PASSOU: Diferença aceitável")
            return True
        else:
            print(f"❌ FALHOU: Diferença muito grande")
            return False
            
    except Exception as e:
        print(f"❌ ERRO: {str(e)}")
        return False

def main():
    """Executa suite completa de testes"""
    print("🚀 INICIANDO TESTES ABRANGENTES DE ANTI-TRUNCAMENTO")
    
    test_scenarios = [
        ("Teste Básico - 5s", 5, "Olá mundo"),
        ("Teste Médio - 30s", 30, "Este é um texto de teste médio com várias palavras"),
        ("Teste Longo - 72s", 72, "Este é um texto muito longo para simular o cenário real onde o usuário reportou truncamento de setenta e dois segundos para sessenta segundos perdendo doze segundos importantes"),
        ("Teste Curto - 2s", 2, "Oi"),
        ("Teste Palavra Única - 10s", 10, "Supercalifragilisticoexpialidocious"),
        ("Teste Múltiplas Palavras - 60s", 60, "Primeira segunda terceira quarta quinta sexta sétima oitava nona décima décima primeira décima segunda palavra"),
        ("Teste Aleatório - 45s", 45, "Palavra um dois três quatro cinco seis sete oito nove dez onze doze treze quatorze quinze")
    ]
    
    passed = 0
    total = len(test_scenarios)
    
    for name, duration, text in test_scenarios:
        if run_test_scenario(name, duration, text):
            passed += 1
    
    print(f"\n{'='*60}")
    print(f"📈 RESULTADOS FINAIS")
    print(f"{'='*60}")
    print(f"✅ Passou: {passed}/{total} testes")
    print(f"❌ Falhou: {total - passed}/{total} testes")
    print(f"📊 Taxa de sucesso: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print(f"\n🎉 TODOS OS TESTES PASSARAM!")
        print(f"   O sistema de anti-truncamento está funcionando corretamente.")
    else:
        print(f"\n⚠️  ALGUNS TESTES FALHARAM!")
        print(f"   Verificar logs acima para detalhes.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)