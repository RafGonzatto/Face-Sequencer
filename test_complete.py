#!/usr/bin/env python3
"""Complete test to generate MP4 from Portuguese text"""
import requests
import json
import time
import os

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

def test_full_workflow():
    print("🎬 COMPLETE MP4 GENERATION TEST")
    print("=" * 50)
    
    # Step 1: Update project
    print("\n1. 📝 Setting up project with Portuguese text...")
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
        if response.status_code != 200:
            print(f"❌ Project setup failed: {response.text}")
            return False
        print("✅ Project setup successful!")
    except Exception as e:
        print(f"❌ Error setting up project: {e}")
        return False
    
    # Step 2: Scan folder
    print("\n2. 🔍 Scanning images folder...")
    try:
        response = requests.post(f"{base_url}/api/folder/scan", json={"path": "images"})
        if response.status_code != 200:
            print(f"❌ Folder scan failed: {response.text}")
            return False
        
        result = response.json()
        mapping = result.get('mapping', {})
        print(f"✅ Found images for characters: {', '.join(sorted(mapping.keys()))}")
    except Exception as e:
        print(f"❌ Error scanning folder: {e}")
        return False
    
    # Step 3: Build sequence
    print("\n3. 🎯 Building animation sequence...")
    try:
        response = requests.post(f"{base_url}/api/sequence/build")
        if response.status_code != 200:
            print(f"❌ Sequence building failed: {response.text}")
            return False
        
        result = response.json()
        sequence = result.get('sequence', [])
        print(f"✅ Generated sequence with {len(sequence)} frames")
        
        # Show character distribution
        char_count = {}
        for frame in sequence:
            char = frame.get('char', ' ')
            char_count[char] = char_count.get(char, 0) + 1
        
        print("📊 Character distribution:")
        for char, count in sorted(char_count.items())[:10]:  # Top 10
            display_char = 'SPACE' if char == ' ' else char
            print(f"   {display_char}: {count} frames")
        if len(char_count) > 10:
            print(f"   ... and {len(char_count) - 10} more characters")
        
    except Exception as e:
        print(f"❌ Error building sequence: {e}")
        return False
    
    # Step 4: Export MP4
    print("\n4. 🎥 Exporting MP4 video...")
    export_data = {
        "format": "mp4",
        "fps": 10,
        "quality": "medium",
        "background": "transparent"
    }
    
    try:
        response = requests.post(f"{base_url}/api/export/video", json=export_data)
        if response.status_code != 200:
            print(f"❌ MP4 export failed: {response.text}")
            return False
        
        result = response.json()
        task_id = result.get('task_id')
        print(f"✅ Export started! Task ID: {task_id}")
        
        # Check export status
        print("⏳ Waiting for export to complete...")
        for i in range(30):  # Wait up to 30 seconds
            time.sleep(1)
            try:
                status_response = requests.get(f"{base_url}/api/export/status/{task_id}")
                if status_response.status_code == 200:
                    status_result = status_response.json()
                    if status_result.get('complete'):
                        output_file = status_result.get('output_file', 'output.mp4')
                        print(f"🎉 Export completed! File: {output_file}")
                        
                        # Check if file exists
                        if os.path.exists(output_file):
                            file_size = os.path.getsize(output_file)
                            print(f"📁 File size: {file_size:,} bytes")
                            print(f"📂 Full path: {os.path.abspath(output_file)}")
                        else:
                            print(f"⚠️  File not found at expected location: {output_file}")
                        
                        return True
                    else:
                        progress = status_result.get('progress', 0)
                        print(f"   Progress: {progress:.1f}%", end='\r')
                else:
                    print(f"❌ Status check failed: {status_response.text}")
                    return False
            except Exception as e:
                print(f"❌ Error checking status: {e}")
                return False
        
        print("\n⏰ Export timeout - check manually")
        return False
        
    except Exception as e:
        print(f"❌ Error exporting video: {e}")
        return False

def main():
    success = test_full_workflow()
    
    print("\n" + "=" * 50)
    if success:
        print("🏆 SUCCESS! Your Portuguese lip-sync animation has been generated!")
        print("🎬 The MP4 file should be in the current directory.")
        print("📝 Text used: Portuguese game development tutorial")
        print("🖼️  Images: Character mappings from 'images' folder")
    else:
        print("❌ FAILED! Check the error messages above.")
    print("=" * 50)

if __name__ == "__main__":
    main()