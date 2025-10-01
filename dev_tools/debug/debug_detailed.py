#!/usr/bin/env python3
"""
Debug especial para encontrar onde está sendo gerado o erro "No frame states available"
"""

import json
import requests
import traceback

BASE_URL = "http://localhost:5000"

def debug_detailed_build_sequence():
    """Debug super detalhado para encontrar a origem do erro"""
    print("=== DEBUG DETALHADO: Rastreamento do erro ===")
    
    # Teste 1: Dados básicos sem frame_states
    test_data = {
        "text": "TESTE",
        "text_driven": True
    }
    
    try:
        print("\n1️⃣ Testando com dados básicos...")
        response = requests.post(
            f"{BASE_URL}/api/sequence/build-from-audio",
            json=test_data,
            headers={'Content-Type': 'application/json'}
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        # Teste 2: Com frame_states vazios
        test_data_empty = {
            "text": "TESTE",
            "text_driven": True,
            "frame_states": []
        }
        
        print("\n2️⃣ Testando com frame_states vazios...")
        response2 = requests.post(
            f"{BASE_URL}/api/sequence/build-from-audio",
            json=test_data_empty,
            headers={'Content-Type': 'application/json'}
        )
        
        print(f"Status: {response2.status_code}")
        print(f"Response: {response2.text}")
        
        # Teste 3: Com alignment_results vazios
        test_data_alignment = {
            "text": "TESTE",
            "text_driven": True,
            "alignment_results": {
                "frame_states": []
            }
        }
        
        print("\n3️⃣ Testando com alignment_results vazios...")
        response3 = requests.post(
            f"{BASE_URL}/api/sequence/build-from-audio",
            json=test_data_alignment,
            headers={'Content-Type': 'application/json'}
        )
        
        print(f"Status: {response3.status_code}")
        print(f"Response: {response3.text}")
        
    except Exception as e:
        print(f"Erro na requisição: {e}")
        traceback.print_exc()

def check_server_logs():
    """Tenta verificar se há logs no servidor"""
    print("\n=== Verificando estado do servidor ===")
    
    try:
        # Teste de health check
        response = requests.get(f"{BASE_URL}/api/health")
        if response.status_code == 200:
            print("✅ Servidor está funcionando")
        
        # Verifica o estado do projeto atual
        response = requests.get(f"{BASE_URL}/api/project")
        if response.status_code == 200:
            data = response.json()
            project_data = data.get('data', {})
            print(f"📊 Estado do projeto:")
            print(f"  - text: '{project_data.get('text', '')}'")
            print(f"  - sequence: {len(project_data.get('sequence', []))} frames")
            print(f"  - frame_states: {len(project_data.get('frame_states', []))} estados")
            print(f"  - letter_map: {len(project_data.get('letter_map', {}))} letras")
        
    except Exception as e:
        print(f"Erro verificando servidor: {e}")

if __name__ == "__main__":
    check_server_logs()
    debug_detailed_build_sequence()