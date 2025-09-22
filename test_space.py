#!/usr/bin/env python3
"""Test the new space image functionality"""
import requests
import json

base_url = "http://localhost:5000"

def test_space_functionality():
    print("🚀 TESTING SPACE IMAGE FUNCTIONALITY")
    print("=" * 45)
    
    # Test basic setup
    print("\n1. 🏗️ Setting up project...")
    project_data = {
        "text": "HELLO WORLD TEST",
        "folder_path": "images",
        "settings": {
            "frame_duration": 100,
            "pause_duration": 50
        }
    }
    
    try:
        response = requests.post(f"{base_url}/api/project", json=project_data)
        if response.status_code == 200:
            print("   ✅ Project setup successful!")
        else:
            print(f"   ❌ Project setup failed: {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    # Test folder scan
    print("\n2. 🔍 Scanning images...")
    try:
        response = requests.post(f"{base_url}/api/folder/scan", json={"path": "images"})
        if response.status_code == 200:
            result = response.json()
            mapping = result.get('mapping', {})
            print(f"   ✅ Found {len(mapping)} character mappings")
            print(f"   📋 Characters: {', '.join(sorted(mapping.keys()))}")
        else:
            print(f"   ❌ Folder scan failed: {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    # Test sequence building
    print("\n3. 🎬 Building sequence...")
    try:
        response = requests.post(f"{base_url}/api/sequence/build")
        if response.status_code == 200:
            result = response.json()
            sequence = result.get('sequence', [])
            print(f"   ✅ Generated sequence with {len(sequence)} frames")
            
            # Count spaces and letters
            space_count = sum(1 for frame in sequence if frame.get('char') == ' ')
            letter_count = len(sequence) - space_count
            print(f"   📊 Letters: {letter_count} frames")
            print(f"   📊 Spaces: {space_count} frames")
            
            # Show first few frames
            print("   🎞️ First 5 frames:")
            for i, frame in enumerate(sequence[:5]):
                char = frame.get('char')
                if char == ' ':
                    char = 'SPACE'
                duration = frame.get('duration', 0)
                filename = frame.get('filename', 'None')
                print(f"      Frame {i+1}: '{char}' ({duration}ms) - {filename}")
            
        else:
            print(f"   ❌ Sequence building failed: {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    return True

def test_interface_elements():
    print("\n4. 🖥️ INTERFACE ELEMENTS TO TEST:")
    print("   • Space Image section added below Fallback Image")
    print("   • 'Choose Space Image' button")
    print("   • 'Clear' button for space image")
    print("   • SPACE item in Character Mapping grid")
    print("   • Click SPACE item to select image")
    print("   • Drag & drop image to SPACE item")
    
    print("\n📋 HOW TO TEST IN BROWSER:")
    print("1. Go to http://localhost:5000")
    print("2. Click '🧪 Test Mode' to load Portuguese text")
    print("3. Look for new 'Space Image' section in left panel")
    print("4. Look for 'SPACE' item in Character Mapping grid")
    print("5. Click 'Choose Space Image' to upload image for spaces")
    print("6. Or click the SPACE grid item to upload")
    print("7. Build sequence and see space frames use your image")

if __name__ == "__main__":
    success = test_space_functionality()
    
    if success:
        print("\n🎉 API FUNCTIONALITY WORKING!")
        test_interface_elements()
    else:
        print("\n❌ API issues detected.")
    
    print("\n" + "=" * 45)
    print("🎯 Ready for testing! Open http://localhost:5000")
    print("=" * 45)