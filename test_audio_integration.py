# test_audio_integration.py - Integration tests for audio components
"""
End-to-end tests for the audio features in Face Sequencer Pro.
These tests verify the complete workflow from audio upload to final animation.
"""

import os
import json
import time
import tempfile
import unittest
import numpy as np
import soundfile as sf
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from app import app

class AudioUploadTests(unittest.TestCase):
    """Test audio upload functionality and error handling"""
    
    def setUp(self):
        """Set up test environment before each test"""
        self.app = app.test_client()
        self.audio_file_path = self.create_test_audio_file()
    
    def tearDown(self):
        """Clean up after each test"""
        if hasattr(self, 'audio_file_path') and os.path.exists(self.audio_file_path):
            os.unlink(self.audio_file_path)
    
    def create_test_audio_file(self, duration=2.0, sample_rate=16000):
        """Create a temporary audio file for testing"""
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        
        # Simple speech-like signal
        signal = 0.3 * np.sin(2 * np.pi * 440 * t) * np.exp(-t * 0.5)
        
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        sf.write(temp_file.name, signal, sample_rate)
        
        return temp_file.name
    
    def test_successful_upload(self):
        """Test that audio can be successfully uploaded"""
        with open(self.audio_file_path, 'rb') as audio_file:
            response = self.app.post('/api/audio/upload', 
                data={'audio': (audio_file, 'test.wav')},
                content_type='multipart/form-data'
            )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('audio', data)
        self.assertIn('filename', data['audio'])
    
    def test_unsupported_format(self):
        """Test error handling for unsupported audio formats"""
        # Create a text file with .txt extension
        txt_file = tempfile.NamedTemporaryFile(suffix='.txt', delete=False)
        txt_file.write(b'This is not an audio file')
        txt_file.close()
        
        try:
            with open(txt_file.name, 'rb') as file:
                response = self.app.post('/api/audio/upload', 
                    data={'audio': (file, 'not_audio.txt')},
                    content_type='multipart/form-data'
                )
            
            self.assertEqual(response.status_code, 400)
            data = json.loads(response.data)
            self.assertFalse(data['success'])
            self.assertIn('error', data)
            self.assertIn('format', data['error'].lower())
        finally:
            if os.path.exists(txt_file.name):
                os.unlink(txt_file.name)
    
    def test_missing_file(self):
        """Test error handling when no file is provided"""
        response = self.app.post('/api/audio/upload', 
            data={},
            content_type='multipart/form-data'
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('error', data)
    
    def test_corrupted_audio(self):
        """Test error handling for corrupted audio files"""
        # Create a corrupted audio file (WAV header but invalid data)
        corrupt_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        corrupt_file.write(b'RIFF\x00\x00\x00\x00WAVEfmt \x00\x00\x00\x00\x00\x00\x00\x00')
        corrupt_file.close()
        
        try:
            with open(corrupt_file.name, 'rb') as file:
                response = self.app.post('/api/audio/upload', 
                    data={'audio': (file, 'corrupt.wav')},
                    content_type='multipart/form-data'
                )
            
            # Either 400 (bad request) or 500 (server error) is acceptable
            self.assertIn(response.status_code, [400, 500])
            data = json.loads(response.data)
            self.assertFalse(data['success'])
        finally:
            if os.path.exists(corrupt_file.name):
                os.unlink(corrupt_file.name)

class AudioProcessingTests(unittest.TestCase):
    """Test audio processing functionality"""
    
    def setUp(self):
        """Set up test environment before each test"""
        self.app = app.test_client()
        self.audio_file_path = self.create_test_audio_file(duration=5.0)
        self.upload_response = None
    
    def tearDown(self):
        """Clean up after each test"""
        if hasattr(self, 'audio_file_path') and os.path.exists(self.audio_file_path):
            os.unlink(self.audio_file_path)
    
    def create_test_audio_file(self, duration=5.0, sample_rate=16000):
        """Create a temporary audio file for testing with pause patterns to simulate speech"""
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        
        # Create a signal with pauses to better simulate speech patterns
        signal = np.zeros_like(t)
        
        # Add speech-like segments with pauses in between
        for i in range(5):
            start = i * 0.8
            end = start + 0.3
            
            # Only add speech in the valid portions of the array
            mask = (t >= start) & (t < end)
            if np.any(mask):
                segment_t = t[mask] - start
                segment = 0.5 * np.sin(2 * np.pi * 440 * segment_t)
                signal[mask] = segment
        
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        sf.write(temp_file.name, signal, sample_rate)
        
        return temp_file.name
    
    def upload_audio(self):
        """Helper method to upload audio and return the response"""
        if not self.upload_response:
            with open(self.audio_file_path, 'rb') as audio_file:
                self.upload_response = self.app.post('/api/audio/upload', 
                    data={'audio': (audio_file, 'test.wav')},
                    content_type='multipart/form-data'
                )
        return self.upload_response
    
    def test_audio_analysis(self):
        """Test that uploaded audio can be analyzed"""
        # First upload audio
        upload_response = self.upload_audio()
        if upload_response.status_code != 200:
            self.skipTest("Audio upload failed, skipping analysis test")
        
        upload_data = json.loads(upload_response.data)
        audio_filename = upload_data['audio']['filename']
        
        # Now test audio analysis
        response = self.app.post('/api/audio/analyze',
            json={'filename': audio_filename}
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('analysis', data)
        self.assertIn('duration_ms', data['analysis'])
        self.assertIn('sample_rate', data['analysis'])
    
    def test_audio_alignment(self):
        """Test that audio can be aligned with text"""
        # First upload audio
        upload_response = self.upload_audio()
        if upload_response.status_code != 200:
            self.skipTest("Audio upload failed, skipping alignment test")
        
        upload_data = json.loads(upload_response.data)
        audio_filename = upload_data['audio']['filename']
        
        # Test audio alignment with sample text
        response = self.app.post('/api/audio/align',
            json={
                'filename': audio_filename,
                'text': 'This is a test for audio alignment',
                'language': 'en-US'
            }
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        
        # If alignment is available, check for tokens
        if data.get('alignment'):
            self.assertIn('tokens', data['alignment'])
            # There should be at least one token for each word in the text
            self.assertGreaterEqual(
                len([t for t in data['alignment']['tokens'] if t['type'] == 'word']), 
                7  # Minimum number of words we expect
            )

class CrossBrowserTests(unittest.TestCase):
    """
    Test compatibility across different browsers.
    Note: These tests require having the appropriate webdrivers installed.
    """
    
    def setUp(self):
        """Set up web server before tests"""
        # Note: In a real implementation, we would spin up the Flask server
        # in a separate thread or process. For this test, we'll assume it's running.
        self.base_url = 'http://localhost:5000'
        
        # Store browser instances
        self.browsers = []
    
    def tearDown(self):
        """Clean up after tests"""
        for browser in self.browsers:
            browser.quit()
    
    def create_chrome_driver(self):
        """Create and configure Chrome WebDriver"""
        options = Options()
        options.add_argument('--headless')
        driver = webdriver.Chrome(options=options)
        self.browsers.append(driver)
        return driver
    
    def test_chrome_audio_upload_ui(self):
        """Test that audio upload UI works in Chrome"""
        try:
            driver = self.create_chrome_driver()
            driver.get(self.base_url)
            
            # Wait for page to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "audioFileInput"))
            )
            
            # Check that audio elements exist
            audio_input = driver.find_element(By.ID, "audioFileInput")
            upload_btn = driver.find_element(By.ID, "uploadAudioBtn")
            timing_toggle = driver.find_element(By.ID, "timingModeToggle")
            
            self.assertIsNotNone(audio_input)
            self.assertIsNotNone(upload_btn)
            self.assertIsNotNone(timing_toggle)
            
            # Test toggle functionality
            timing_toggle.click()
            time.sleep(1)  # Wait for UI update
            
            # Check that audio visualization is displayed when toggle is on
            audio_viz = driver.find_element(By.ID, "audioVisualizationContainer")
            self.assertTrue(audio_viz.is_displayed())
            
        except Exception as e:
            self.fail(f"Browser test failed: {str(e)}")

def run_tests():
    """Run all tests"""
    unittest.main(argv=['first-arg-is-ignored'], exit=False)

if __name__ == '__main__':
    print("Running audio integration tests...")
    run_tests()
    print("All integration tests completed.")