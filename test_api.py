#!/usr/bin/env python3
"""Test script to verify the API functionality"""
import requests
import json

# Test data
test_text = '''"COMO COMEÇAR A FAZER UM JOGO DO JEITO CERTO"

Três pontos:
Primeiro, ter um batatador — um computador com poder de processamento mínimo de uma batata.
Segundo, entender que qualquer pessoa pode fazer isso — o segredo não é ser gênio, é só começar.
Terceiro, e o principal: ser lei — ter força de vontade e determinação.

Primeiro, no seu batatador, baixe dois programas:
Primeiro, o VS Code — é onde a mágica vai acontecer.
Segundo, o Node.js.

Se sentir dificuldade ou encontrar algum problema, manda nos comentários que a gente ajuda.

Agora, dentro do VS Code, clique no ícone que parece o Tetris e abra a aba de extensões.
Escreva Live Server e instale.
Isso vai servir pra rodar nosso projeto.'''

base_url = "http://localhost:5000"

def test_api():
    print("Testing Face Sequencer API...")
    
    # Step 1: Update project
    print("\n1. Updating project with test data...")
    project_data = {
        "text": test_text,
        "folder_path": "images",
        "settings": {
            "frame_duration": 100,
            "pause_duration": 50
        }
    }
    
    try:
        response = requests.post(f"{base_url}/api/project", json=project_data)
        print(f"Project update status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Success: {result.get('success', False)}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Error updating project: {e}")
        return
    
    # Step 2: Scan folder
    print("\n2. Scanning images folder...")
    try:
        response = requests.post(f"{base_url}/api/folder/scan", json={"path": "images"})
        print(f"Folder scan status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Success: {result.get('success', False)}")
            mapping = result.get('mapping', {})
            print(f"Found {len(mapping)} character mappings")
            for char, info in mapping.items():
                filename = info.get('filename', 'None') if isinstance(info, dict) else str(info)
                print(f"  {char}: {filename}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Error scanning folder: {e}")
        return
    
    # Step 3: Build sequence
    print("\n3. Building sequence...")
    try:
        response = requests.post(f"{base_url}/api/sequence/build")
        print(f"Build sequence status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Success: {result.get('success', False)}")
            sequence = result.get('sequence', [])
            print(f"Generated sequence with {len(sequence)} frames")
            # Show first few frames
            for i, frame in enumerate(sequence[:5]):
                char = frame.get('char', '?')
                duration = frame.get('duration', 0)
                filename = frame.get('filename', 'None')
                print(f"  Frame {i}: '{char}' ({duration}ms) - {filename}")
            if len(sequence) > 5:
                print(f"  ... and {len(sequence) - 5} more frames")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Error building sequence: {e}")
        return
    
    print("\n✅ API test completed!")

if __name__ == "__main__":
    test_api()