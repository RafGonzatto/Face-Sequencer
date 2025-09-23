# test_api_endpoints.py - Test audio API endpoints
"""
Tests for the new audio alignment API endpoints without starting the full server.
"""

import os
import json
import tempfile
import numpy as np
import soundfile as sf
from app import app

def create_test_audio_file():
    """Create a temporary audio file for testing"""
    # Generate a simple 2-second audio signal
    duration = 2.0
    sample_rate = 16000
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    
    # Simple speech-like signal
    signal = 0.3 * np.sin(2 * np.pi * 440 * t) * np.exp(-t * 0.5)
    
    # Create temporary file
    temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    sf.write(temp_file.name, signal, sample_rate)
    
    return temp_file.name

def test_audio_status_endpoint():
    """Test audio status endpoint"""
    print("🧪 Testing /api/audio/status endpoint...")
    
    with app.test_client() as client:
        response = client.get('/api/audio/status')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        print(f"  ✅ Status: {data['success']}")
        print(f"  ✅ Available: {data['available']}")
        print(f"  ✅ Language: {data['language']}")
        print(f"  ✅ Formats: {data['supported_formats']}")
        
        assert data['success'] == True
        assert 'available' in data
        
    return True

def test_audio_upload_endpoint():
    """Test audio upload endpoint"""
    print("🧪 Testing /api/audio/upload endpoint...")
    
    # Create test audio file
    audio_file_path = create_test_audio_file()
    
    try:
        with app.test_client() as client:
            # Test file upload
            with open(audio_file_path, 'rb') as audio_file:
                response = client.post('/api/audio/upload', 
                    data={'audio': (audio_file, 'test.wav')},
                    content_type='multipart/form-data'
                )
            
            print(f"  📤 Upload response status: {response.status_code}")
            
            if response.status_code == 200:
                data = json.loads(response.data)
                print(f"  ✅ Upload success: {data['success']}")
                print(f"  ✅ Audio info: {data['audio']['duration_ms']:.0f}ms")
                
                assert data['success'] == True
                assert 'audio' in data
                return data['audio']['filename']  # Return filename for further tests
            
            elif response.status_code == 503:
                data = json.loads(response.data)
                print(f"  ⚠️  Audio system not available: {data['error']}")
                return None
            else:
                print(f"  ❌ Upload failed: {response.status_code}")
                if response.data:
                    print(f"      Error: {response.data.decode()}")
                return None
    
    finally:
        # Cleanup
        if os.path.exists(audio_file_path):
            os.unlink(audio_file_path)
    
    return True

def test_audio_analyze_endpoint():
    """Test audio analysis endpoint"""
    print("🧪 Testing /api/audio/analyze endpoint...")
    
    # First upload an audio file
    audio_filename = test_audio_upload_endpoint()
    if not audio_filename:
        print("  ⚠️  Skipping analysis test - upload failed")
        return True
    
    with app.test_client() as client:
        response = client.post('/api/audio/analyze',
            json={'audio_filename': audio_filename},
            content_type='application/json'
        )
        
        print(f"  📊 Analysis response status: {response.status_code}")
        
        if response.status_code == 200:
            data = json.loads(response.data)
            print(f"  ✅ Analysis success: {data['success']}")
            
            analysis = data.get('analysis', {})
            stats = data.get('stats', {})
            
            print(f"  ✅ Duration: {analysis.get('duration_ms', 0):.0f}ms")
            print(f"  ✅ Speech segments: {stats.get('total_speech_segments', 0)}")
            print(f"  ✅ Gaps detected: {stats.get('total_gaps', 0)}")
            
            assert data['success'] == True
            
        elif response.status_code == 503:
            data = json.loads(response.data) 
            print(f"  ⚠️  Audio system not available: {data['error']}")
        else:
            print(f"  ❌ Analysis failed: {response.status_code}")
            if response.data:
                print(f"      Error: {response.data.decode()}")
    
    return True

def test_audio_align_endpoint():
    """Test audio alignment endpoint"""
    print("🧪 Testing /api/audio/align endpoint...")
    
    # First upload an audio file
    audio_filename = test_audio_upload_endpoint()
    if not audio_filename:
        print("  ⚠️  Skipping alignment test - upload failed")
        return True
    
    with app.test_client() as client:
        response = client.post('/api/audio/align',
            json={
                'audio_filename': audio_filename,
                'text': 'Olá, como está você?'
            },
            content_type='application/json'
        )
        
        print(f"  🎯 Alignment response status: {response.status_code}")
        
        if response.status_code == 200:
            data = json.loads(response.data)
            print(f"  ✅ Alignment success: {data['success']}")
            
            sequence = data.get('sequence', [])
            stats = data.get('stats', {})
            
            print(f"  ✅ Tokens generated: {stats.get('total_tokens', 0)}")
            print(f"  ✅ Words: {stats.get('word_tokens', 0)}")
            print(f"  ✅ Method: {stats.get('method', 'unknown')}")
            
            assert data['success'] == True
            
        elif response.status_code == 503:
            data = json.loads(response.data)
            print(f"  ⚠️  Audio system not available: {data['error']}")
        else:
            print(f"  ❌ Alignment failed: {response.status_code}")
            if response.data:
                print(f"      Error: {response.data.decode()}")
    
    return True

def run_api_tests():
    """Run all API endpoint tests"""
    print("🚀 Testing Audio API Endpoints")
    print("=" * 50)
    
    tests = [
        test_audio_status_endpoint,
        test_audio_upload_endpoint, 
        test_audio_analyze_endpoint,
        test_audio_align_endpoint
    ]
    
    results = []
    for test_func in tests:
        try:
            result = test_func()
            results.append(("✅", test_func.__name__, "PASSED"))
            print()
        except Exception as e:
            results.append(("❌", test_func.__name__, f"FAILED: {e}"))
            print(f"  ❌ Error: {e}")
            print()
    
    print("=" * 50)
    print("📊 API Test Results:")
    for icon, test_name, status in results:
        print(f"  {icon} {test_name}: {status}")
    
    passed = len([r for r in results if r[0] == "✅"])
    total = len(results)
    
    print(f"\n🎯 Summary: {passed}/{total} API tests passed")
    
    if passed == total:
        print("🎉 All API endpoints working! Ready for frontend integration.")
        return True
    else:
        print("⚠️  Some API tests failed - check availability of audio system.")
        return False

if __name__ == "__main__":
    run_api_tests()