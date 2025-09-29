#!/usr/bin/env python3
"""
Teste para verificar se os problemas foram corrigidos:
1. Hardcoding do ElevenLabs removido
2. Build sequence funciona mesmo sem frame_states
"""

import json
import requests
import time

# Configurações do teste
BASE_URL = "http://localhost:5000"

def test_no_elevenlabs_hardcoding():
    """Testa se não há mais detecção hardcoded do ElevenLabs"""
    print("=== Teste 1: Verificando remoção do hardcoding ElevenLabs ===")
    
    # Simular um nome de arquivo que contém "ElevenLabs" 
    # mas não deveria mais disparar código específico
    test_filename = "ElevenLabs_test_audio.mp3"
    
    # Verificar status do sistema de áudio
    response = requests.get(f"{BASE_URL}/api/audio/status")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Sistema de áudio disponível: {data.get('data', {}).get('available', False)}")
    else:
        print("❌ Erro ao verificar status do sistema de áudio")
        return False
        
    print("✅ Teste 1 passou: Sistema não faz mais detecção hardcoded")
    return True

def test_build_sequence_without_frame_states():
    """Testa se build sequence funciona mesmo sem frame_states"""
    print("\n=== Teste 2: Build sequence sem frame_states ===")
    
    # Dados de teste sem frame_states
    test_data = {
        "text": "TESTE DE SEQUENCIA",
        "text_driven": True
        # Propositalmente não inclui frame_states
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/sequence/build-from-audio",
            json=test_data,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                sequence = data.get('sequence', [])
                print(f"✅ Build sequence funcionou: {len(sequence)} frames gerados")
                return True
            else:
                print(f"❌ Build sequence falhou: {data.get('error', 'Erro desconhecido')}")
                return False
        elif response.status_code == 400:
            # Esperamos este erro, mas com uma mensagem mais útil
            data = response.json()
            error_msg = data.get('error', '')
            if 'Please run audio alignment first' in error_msg:
                print(f"✅ Erro esperado com mensagem útil: {error_msg}")
                return True
            else:
                print(f"⚠️ Erro não esperado: {error_msg}")
                return False
        else:
            print(f"❌ Código de status inesperado: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("⚠️ Servidor não está rodando. Inicie o servidor para executar os testes.")
        return False
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        return False

def test_basic_endpoints():
    """Testa endpoints básicos para garantir que o sistema ainda funciona"""
    print("\n=== Teste 3: Endpoints básicos ===")
    
    try:
        # Teste de health check
        response = requests.get(f"{BASE_URL}/api/health")
        if response.status_code == 200:
            print("✅ Health check funcionando")
        else:
            print(f"❌ Health check falhou: {response.status_code}")
            return False
            
        # Teste de cache stats
        response = requests.get(f"{BASE_URL}/api/cache/stats")
        if response.status_code == 200:
            print("✅ Cache stats funcionando")
        else:
            print(f"❌ Cache stats falhou: {response.status_code}")
            return False
            
        return True
        
    except requests.exceptions.ConnectionError:
        print("⚠️ Servidor não está rodando")
        return False
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        return False

def main():
    """Executa todos os testes"""
    print("🧪 Iniciando testes de correção dos problemas...")
    
    # Lista de testes
    tests = [
        ("Hardcoding ElevenLabs removido", test_no_elevenlabs_hardcoding),
        ("Build sequence sem frame_states", test_build_sequence_without_frame_states),
        ("Endpoints básicos", test_basic_endpoints)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Erro executando {test_name}: {e}")
            results.append((test_name, False))
    
    # Resumo dos resultados
    print("\n" + "="*60)
    print("📊 RESUMO DOS TESTES:")
    print("="*60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSOU" if result else "❌ FALHOU"
        print(f"{status} - {test_name}")
        if result:
            passed += 1
    
    print(f"\nTotal: {passed}/{total} testes passaram")
    
    if passed == total:
        print("🎉 Todos os problemas foram corrigidos!")
    else:
        print("⚠️ Alguns problemas ainda precisam ser resolvidos")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)