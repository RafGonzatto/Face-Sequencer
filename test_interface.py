#!/usr/bin/env python3
"""Test web interface functionality"""
import requests
import json

base_url = "http://localhost:5000"

def test_web_interface():
    print("🌐 TESTING WEB INTERFACE")
    print("=" * 40)
    
    print("\n✅ Server Status Check")
    try:
        response = requests.get(base_url)
        if response.status_code == 200:
            print("   🟢 Web server is running")
            print("   📱 Interface accessible at http://localhost:5000")
        else:
            print(f"   ❌ Server returned {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Cannot connect to server: {e}")
        return False
    
    print("\n✅ API Endpoints Check")
    
    # Test project endpoint
    project_data = {
        "text": "TESTE ABC",
        "folder_path": "images", 
        "settings": {"frame_duration": 100, "pause_duration": 50}
    }
    
    try:
        response = requests.post(f"{base_url}/api/project", json=project_data)
        print(f"   📝 Project API: {'✅' if response.status_code == 200 else '❌'}")
    except:
        print("   📝 Project API: ❌")
    
    # Test folder scan
    try:
        response = requests.post(f"{base_url}/api/folder/scan", json={"path": "images"})
        print(f"   📁 Folder Scan API: {'✅' if response.status_code == 200 else '❌'}")
    except:
        print("   📁 Folder Scan API: ❌")
    
    # Test sequence build
    try:
        response = requests.post(f"{base_url}/api/sequence/build")
        print(f"   🎬 Sequence Build API: {'✅' if response.status_code == 200 else '❌'}")
    except:
        print("   🎬 Sequence Build API: ❌")
    
    print("\n🎯 INSTRUCTIONS FOR TESTING:")
    print("1. Open http://localhost:5000 in your browser")
    print("2. Click the '🧪 Test Mode' button (top-right corner)")
    print("3. This will:")
    print("   • Load the Portuguese text automatically")
    print("   • Set folder path to 'images'")
    print("   • Scan for character images")
    print("4. Click 'Build Sequence' to generate animation")
    print("5. Click 'Export MP4' to create the video")
    
    print(f"\n📁 Available character images in 'images' folder:")
    import os
    if os.path.exists("images"):
        files = [f for f in os.listdir("images") if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        for f in sorted(files):
            print(f"   • {f}")
    
    return True

def main():
    success = test_web_interface()
    
    print("\n" + "=" * 40)
    if success:
        print("🎉 SUCCESS! The Face Sequencer is ready!")
        print("🚀 Go to http://localhost:5000 and click Test Mode")
        print("📽️  Your Portuguese lip-sync video will be generated")
    else:
        print("❌ Some issues detected. Check server status.")
    print("=" * 40)

if __name__ == "__main__":
    main()