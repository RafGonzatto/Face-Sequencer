#!/usr/bin/env python3
"""
Teste específico para verificar a correção do problema de truncamento de vídeo
Simula o caso relatado: áudio de 1:12 mas vídeo de apenas 1:00
"""

import sys
import os
import time
import requests
import json

def test_video_duration_fix():
    """Testa se o problema de truncamento foi corrigido"""
    print("\n" + "="*70)
    print("🧪 TESTE: Correção do Problema de Truncamento de Vídeo")
    print("="*70)
    print("📝 Caso: Áudio 1:12 gerando vídeo de apenas 1:00")
    print("🎯 Objetivo: Garantir que vídeo tenha duração completa do áudio")
    print()
    
    base_url = "http://localhost:5000"
    
    # Verificar se servidor está rodando
    try:
        response = requests.get(base_url, timeout=5)
        print("✅ Servidor está rodando")
    except requests.exceptions.RequestException as e:
        print(f"❌ Servidor não está acessível: {e}")
        return False
    
    # Simular dados de teste que replicam o problema relatado
    # Baseado nos logs: 72.06s de áudio, 2162 frame_states, mas apenas 698 frames no vídeo
    test_audio_duration = 72.06  # segundos
    expected_frames = int(test_audio_duration * 30)  # 30 FPS
    
    # Criar frame_states simulados para teste
    frame_states = []
    test_text = "COMO COMEÇAR A FAZER UM JOGO DO JEITO CERTO Três pontos Primeiro ter um batatador um computado"
    words = test_text.split()
    
    # Distribuir palavras ao longo dos frames
    frames_per_word = expected_frames // len(words)
    
    current_frame = 0
    for i, word in enumerate(words):
        word_frames = frames_per_word
        if i == len(words) - 1:  # Última palavra pega os frames restantes
            word_frames = expected_frames - current_frame
        
        for j in range(word_frames):
            frame_state = {
                'ms': 33.33,  # 30 FPS
                'active_word': word,
                'is_pause': False,
                'char': word[0] if word else ' ',
                'timestamp': current_frame / 30.0
            }
            frame_states.append(frame_state)
            current_frame += 1
    
    print(f"📊 Dados de teste criados:")
    print(f"   Duração simulada: {test_audio_duration:.2f}s")
    print(f"   Frame states: {len(frame_states)}")
    print(f"   Palavras no texto: {len(words)}")
    print(f"   Frames esperados: {expected_frames}")
    
    # Testar construção da sequência
    try:
        print(f"\n🔧 Testando construção da sequência...")
        
        # Simular projeto mínimo
        test_project = {
            'letter_map': {chr(65+i): f'image_{chr(65+i)}.jpg' for i in range(26)},
            'fallback_image': 'fallback.jpg',
            'pause_image': 'pause.jpg',
            'special_tokens': {}
        }
        
        # Importar e executar a função diretamente
        sys.path.insert(0, '.')
        from app import build_text_driven_sequence_enhanced
        
        print(f"   Executando build_text_driven_sequence_enhanced...")
        sequence = build_text_driven_sequence_enhanced(
            frame_states, 
            test_text, 
            test_project
        )
        
        # Analisar resultados
        print(f"\n📊 RESULTADOS:")
        print(f"   Frame states originais: {len(frame_states)}")
        print(f"   Sequência gerada: {len(sequence)} frames")
        print(f"   Duração original: {len(frame_states)/30:.2f}s")
        print(f"   Duração da sequência: {len(sequence)/30:.2f}s")
        
        # Verificar se o problema foi corrigido
        duration_difference = abs(len(frame_states) - len(sequence))
        percentage_difference = (duration_difference / len(frame_states)) * 100
        
        print(f"   Diferença: {duration_difference} frames ({percentage_difference:.1f}%)")
        
        # Critérios de sucesso
        success_criteria = [
            (percentage_difference <= 5, f"Diferença <= 5% ({percentage_difference:.1f}%)"),
            (len(sequence) >= len(frame_states) * 0.95, f"Sequência >= 95% do original"),
            (len(sequence) > 0, "Sequência não vazia")
        ]
        
        all_passed = True
        print(f"\n🧪 VALIDAÇÃO:")
        for passed, description in success_criteria:
            status = "✅ PASSOU" if passed else "❌ FALHOU"
            print(f"   {status}: {description}")
            if not passed:
                all_passed = False
        
        if all_passed:
            print(f"\n🎉 TESTE PASSOU! Problema de truncamento foi corrigido!")
            print(f"   → Vídeo terá duração completa correspondente ao áudio")
            return True
        else:
            print(f"\n❌ TESTE FALHOU! Problema de truncamento ainda existe!")
            print(f"   → Vídeo será mais curto que o áudio")
            return False
            
    except Exception as e:
        print(f"❌ Erro durante o teste: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_endpoint_integration():
    """Testa através do endpoint HTTP"""
    print(f"\n🌐 Testando integração via API...")
    
    base_url = "http://localhost:5000"
    
    # Dados de teste via API
    test_data = {
        'text': 'COMO COMEÇAR A FAZER UM JOGO DO JEITO CERTO Três pontos Primeiro ter um batatador um computado',
        'text_driven': True,
        'frame_states': []
    }
    
    # Criar frame_states simulados
    for i in range(2162):  # Número do log original
        test_data['frame_states'].append({
            'ms': 33.33,
            'active_word': 'TESTE',
            'is_pause': i % 30 == 0,  # Pausas ocasionais
            'timestamp': i / 30.0
        })
    
    try:
        print(f"   Enviando requisição para /api/sequence/build-from-audio...")
        response = requests.post(
            f"{base_url}/api/sequence/build-from-audio",
            json=test_data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                sequence = result.get('sequence', [])
                print(f"   ✅ API respondeu com sucesso")
                print(f"   📊 Sequência gerada: {len(sequence)} frames")
                print(f"   📊 Frame states enviados: {len(test_data['frame_states'])}")
                
                truncation = len(test_data['frame_states']) - len(sequence)
                print(f"   📊 Diferença: {truncation} frames ({truncation/30:.2f}s)")
                
                if truncation <= 150:  # Tolerância de 5 segundos
                    print(f"   ✅ Truncamento dentro da tolerância!")
                    return True
                else:
                    print(f"   ❌ Truncamento excessivo: {truncation/30:.1f}s")
                    return False
            else:
                print(f"   ❌ API retornou erro: {result.get('error')}")
                return False
        else:
            print(f"   ❌ Status HTTP: {response.status_code}")
            print(f"   Response: {response.text[:200]}...")
            return False
            
    except Exception as e:
        print(f"   ❌ Erro na requisição: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Iniciando teste de correção do truncamento de vídeo...")
    
    # Teste 1: Função direta
    test1_passed = test_video_duration_fix()
    
    # Teste 2: Endpoint API
    test2_passed = test_endpoint_integration()
    
    print(f"\n" + "="*70)
    print("📋 RESUMO DOS TESTES")
    print("="*70)
    print(f"🧪 Teste de função direta: {'✅ PASSOU' if test1_passed else '❌ FALHOU'}")
    print(f"🌐 Teste de endpoint API: {'✅ PASSOU' if test2_passed else '❌ FALHOU'}")
    
    if test1_passed and test2_passed:
        print(f"\n🎉 TODOS OS TESTES PASSARAM!")
        print(f"✅ Problema de truncamento foi corrigido com sucesso!")
        print(f"🎬 Vídeos agora terão duração completa correspondente ao áudio")
    else:
        print(f"\n❌ ALGUNS TESTES FALHARAM!")
        print(f"⚠️  Problema de truncamento pode ainda existir")
    
    print("="*70)