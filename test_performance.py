"""
Performance testing for the Face Sequencer Pro application
Tests the performance of audio processing and sequence building
"""

import os
import json
import time
import tempfile
import unittest
import numpy as np
import soundfile as sf
from app import app

class PerformanceTests(unittest.TestCase):
    """Performance tests for audio processing and animation sequence generation"""
    
    def setUp(self):
        """Set up test environment"""
        self.app = app.test_client()
        self.audio_files = {}
        
        # Generate test files of different sizes
        self.generate_test_files()
    
    def tearDown(self):
        """Clean up after tests"""
        for size, file_path in self.audio_files.items():
            if os.path.exists(file_path):
                os.unlink(file_path)
    
    def generate_test_files(self):
        """Generate audio files of different sizes for performance testing"""
        # Create different durations
        durations = {
            'small': 3,    # 3 seconds
            'medium': 10,  # 10 seconds
            'large': 30,   # 30 seconds
        }
        
        for size, duration in durations.items():
            self.audio_files[size] = self.create_test_audio(duration)
    
    def create_test_audio(self, duration, sample_rate=16000):
        """Create a test audio file of the specified duration"""
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        
        # Create a signal with speech-like patterns
        signal = np.zeros_like(t)
        
        # Generate "speech" segments at regular intervals
        interval = 0.5  # Speech every 0.5 seconds
        speech_duration = 0.3  # Each "word" is 0.3 seconds
        
        for start in np.arange(0, duration, interval):
            end = start + speech_duration
            if end > duration:
                end = duration
                
            segment_mask = (t >= start) & (t < end)
            segment_t = t[segment_mask] - start
            
            # Create a speech-like segment
            if len(segment_t) > 0:
                segment = 0.5 * np.sin(2 * np.pi * 440 * segment_t)
                signal[segment_mask] = segment
        
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        sf.write(temp_file.name, signal, sample_rate)
        
        return temp_file.name
    
    def test_upload_performance(self):
        """Test audio upload performance with different file sizes"""
        results = {}
        
        for size, file_path in self.audio_files.items():
            # Time the upload operation
            start_time = time.time()
            
            with open(file_path, 'rb') as audio_file:
                response = self.app.post('/api/audio/upload', 
                    data={'audio': (audio_file, f'test_{size}.wav')},
                    content_type='multipart/form-data'
                )
            
            end_time = time.time()
            elapsed = end_time - start_time
            
            # Store results
            response_data = json.loads(response.data)
            success = response_data.get('success', False)
            
            results[size] = {
                'time': elapsed,
                'success': success,
                'status_code': response.status_code
            }
            
            # All uploads should succeed regardless of size (within our test range)
            self.assertTrue(success)
            self.assertEqual(response.status_code, 200)
        
        # Log performance results
        print("\n---- Audio Upload Performance ----")
        print(f"Small file: {results['small']['time']:.3f} seconds")
        print(f"Medium file: {results['medium']['time']:.3f} seconds")
        print(f"Large file: {results['large']['time']:.3f} seconds")
        
        # Basic performance expectations - these thresholds may need adjustment
        # based on the specific system performance
        self.assertLess(results['small']['time'], 2.0, "Small file upload took too long")
        self.assertLess(results['medium']['time'], 5.0, "Medium file upload took too long")
    
    def test_sequence_building_performance(self):
        """Test sequence building performance with different text lengths"""
        text_sizes = {
            'small': 'Hello world',
            'medium': 'The quick brown fox jumps over the lazy dog. ' * 3,
            'large': 'The quick brown fox jumps over the lazy dog. ' * 10
        }
        
        results = {}
        
        for size, text in text_sizes.items():
            # Time the sequence building operation
            start_time = time.time()
            
            response = self.app.post('/api/sequence/build',
                json={
                    'text': text,
                    'timing_mode': 'manual',
                    'frame_duration': 100,
                    'pause_duration': 200
                }
            )
            
            end_time = time.time()
            elapsed = end_time - start_time
            
            # Store results
            response_data = json.loads(response.data)
            success = response_data.get('success', False)
            
            results[size] = {
                'time': elapsed,
                'success': success,
                'status_code': response.status_code,
                'sequence_length': len(response_data.get('sequence', [])) if success else 0
            }
            
            # All sequence builds should succeed
            self.assertTrue(success)
            self.assertEqual(response.status_code, 200)
        
        # Log performance results
        print("\n---- Sequence Building Performance ----")
        print(f"Small text: {results['small']['time']:.3f} seconds, {results['small']['sequence_length']} frames")
        print(f"Medium text: {results['medium']['time']:.3f} seconds, {results['medium']['sequence_length']} frames")
        print(f"Large text: {results['large']['time']:.3f} seconds, {results['large']['sequence_length']} frames")
        
        # Basic performance expectations
        self.assertLess(results['small']['time'], 1.0, "Small sequence build took too long")
        self.assertLess(results['medium']['time'], 2.0, "Medium sequence build took too long")
    
    def test_concurrent_requests(self):
        """Test performance with concurrent requests"""
        import threading
        
        # Number of concurrent requests to simulate
        num_requests = 5
        results = {'success': 0, 'failure': 0, 'times': []}
        
        def make_request():
            """Make a request and record the result"""
            start_time = time.time()
            
            response = self.app.post('/api/sequence/build',
                json={
                    'text': 'Concurrent request test',
                    'timing_mode': 'manual'
                }
            )
            
            end_time = time.time()
            elapsed = end_time - start_time
            
            # Track results
            with threading.Lock():
                results['times'].append(elapsed)
                if response.status_code == 200 and json.loads(response.data).get('success', False):
                    results['success'] += 1
                else:
                    results['failure'] += 1
        
        # Start concurrent threads
        threads = []
        for i in range(num_requests):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Log results
        print("\n---- Concurrent Requests Performance ----")
        print(f"Successful requests: {results['success']}/{num_requests}")
        print(f"Average response time: {sum(results['times']) / len(results['times']):.3f} seconds")
        print(f"Min response time: {min(results['times']):.3f} seconds")
        print(f"Max response time: {max(results['times']):.3f} seconds")
        
        # All requests should succeed
        self.assertEqual(results['success'], num_requests, "Some concurrent requests failed")
        
        # The average response time should be reasonable
        avg_time = sum(results['times']) / len(results['times'])
        self.assertLess(avg_time, 3.0, "Average response time for concurrent requests is too high")

def run_tests():
    """Run all performance tests"""
    unittest.main(argv=['first-arg-is-ignored'], exit=False)

if __name__ == '__main__':
    print("Running performance tests...")
    run_tests()
    print("All performance tests completed.")