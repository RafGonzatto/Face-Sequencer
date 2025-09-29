#!/usr/bin/env python3
"""
Debug do endpoint build sequence para ver a resposta exata
"""

import json
import requests

BASE_URL = "http://localhost:5000"

def debug_build_sequence():
    """Debug detalhado do endpoint build sequence"""
    print("=== DEBUG: Build sequence endpoint ===")
    
    # Dados de teste sem frame_states
    test_data = {
        "text": "TESTE DE SEQUENCIA",
        "text_driven": True
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/sequence/build-from-audio",
            json=test_data,
            headers={'Content-Type': 'application/json'}
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        
        try:
            data = response.json()
            print(f"Response JSON: {json.dumps(data, indent=2)}")
        except:
            print(f"Response Text: {response.text}")
            
        return response.status_code, response.text
        
    except Exception as e:
        print(f"Erro na requisição: {e}")
        return None, str(e)

if __name__ == "__main__":
    debug_build_sequence()