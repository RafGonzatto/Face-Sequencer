# test_sequence_building.py - Test sequence building with audio timing
"""
Tests the sequence building functionality with audio-driven timing.
These tests verify that the animation sequence is properly synchronized 
with the audio timing data.
"""

import os
import json
import tempfile
import unittest
import numpy as np
import soundfile as sf
from app import app

class SequenceBuildingTests(unittest.TestCase):
    """Test sequence building with audio-driven timing"""
    
    def setUp(self):
        """Set up test environment before each test"""
        self.app = app.test_client()
        self.audio_file_path = self.create_test_audio_file()
        self.uploaded_filename = self.upload_audio_file()
    
    def tearDown(self):
        """Clean up after each test"""
        if hasattr(self, 'audio_file_path') and os.path.exists(self.audio_file_path):
            os.unlink(self.audio_file_path)
    
    def create_test_audio_file(self, duration=3.0, sample_rate=16000):
        """Create a temporary audio file with speech-like patterns"""
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        
        # Create a signal with pauses to better simulate speech patterns
        signal = np.zeros_like(t)
        
        # Add speech-like segments with pauses in between to simulate words
        # This creates 5 "words" with clear boundaries
        word_times = [(0.2, 0.5), (0.8, 1.1), (1.4, 1.7), (2.0, 2.3), (2.6, 2.9)]
        
        for start, end in word_times:
            mask = (t >= start) & (t < end)
            if np.any(mask):
                segment_t = t[mask] - start
                segment = 0.5 * np.sin(2 * np.pi * 440 * segment_t)
                signal[mask] = segment
        
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        sf.write(temp_file.name, signal, sample_rate)
        
        return temp_file.name
    
    def upload_audio_file(self):
        """Upload the test audio file and return the filename"""
        with open(self.audio_file_path, 'rb') as audio_file:
            response = self.app.post('/api/audio/upload', 
                data={'audio': (audio_file, 'test_sequence.wav')},
                content_type='multipart/form-data'
            )
        
        if response.status_code != 200:
            return None
            
        data = json.loads(response.data)
        return data['audio']['filename'] if data.get('success') else None
    
    def align_audio_with_text(self, text='one two three four five'):
        """Align audio with text and return alignment data"""
        if not self.uploaded_filename:
            self.skipTest("Audio upload failed, skipping alignment test")
        
        response = self.app.post('/api/audio/align',
            json={
                'filename': self.uploaded_filename,
                'text': text
            }
        )
        
        if response.status_code != 200:
            return None
            
        data = json.loads(response.data)
        return data.get('alignment')
    
    def test_sequence_building_with_audio(self):
        """Test building an animation sequence using audio timing"""
        # First align audio with text
        alignment = self.align_audio_with_text()
        if not alignment:
            self.skipTest("Audio alignment failed, skipping sequence building test")
        
        # Now build a sequence using the alignment
        response = self.app.post('/api/sequence/build-from-audio',
            json={
                'text': 'one two three four five',
                'audio_file_id': self.uploaded_filename,
                'alignment_id': alignment.get('id')
            }
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('sequence', data)
        
        sequence = data['sequence']
        self.assertGreater(len(sequence), 0)
        
        # Check that the sequence has at least as many frames as we have words
        # (5 words plus some potential pause frames)
        self.assertGreaterEqual(len(sequence), 5)
        
        # Check that each frame has timing information
        for frame in sequence:
            self.assertIn('duration', frame)
            self.assertIn('image_path', frame)
    
    def test_sequence_timing_matches_audio(self):
        """Test that the sequence timing matches the audio alignment"""
        # First align audio with text
        alignment = self.align_audio_with_text()
        if not alignment:
            self.skipTest("Audio alignment failed, skipping sequence timing test")
        
        # Get token timings from alignment
        word_tokens = [t for t in alignment['tokens'] if t['type'] == 'word']
        
        # Now build a sequence using the alignment
        response = self.app.post('/api/sequence/build-from-audio',
            json={
                'text': 'one two three four five',
                'audio_file_id': self.uploaded_filename,
                'alignment_id': alignment.get('id')
            }
        )
        
        data = json.loads(response.data)
        sequence = data['sequence']
        
        # Calculate total duration of sequence
        sequence_duration = sum(frame['duration'] for frame in sequence)
        
        # Calculate total duration from alignment tokens
        if word_tokens:
            alignment_duration = word_tokens[-1]['end_ms'] - word_tokens[0]['start_ms']
            
            # The sequence duration should be approximately equal to the alignment duration
            # Allow for some small differences due to rounding, etc.
            self.assertAlmostEqual(
                sequence_duration, 
                alignment_duration, 
                delta=100  # Allow 100ms difference
            )
    
    def test_fallback_timing_on_alignment_failure(self):
        """Test that the system falls back to manual timing if alignment fails"""
        # First set up a project with text and settings
        self.app.post('/api/project', 
            json={
                'text': 'one two three four five',
                'settings': {
                    'frame_duration': 100,
                    'pause_duration': 50
                }
            }
        )
        
        # Now attempt to build a sequence with invalid audio data
        response = self.app.post('/api/sequence/build-from-audio',
            json={
                'text': 'one two three four five',
                'audio_file_id': 'nonexistent_file.wav'
            }
        )
        
        # Check that it falls back to manual timing
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        # It should still succeed, just using manual timing
        self.assertTrue(data['success'])
        self.assertIn('sequence', data)
        self.assertIn('fallback_to_manual', data)
        self.assertTrue(data['fallback_to_manual'])
        
        # Sequence should have frames based on manual timing
        sequence = data['sequence']
        self.assertGreater(len(sequence), 0)

class PlaybackSyncTests(unittest.TestCase):
    """Test synchronization between audio playback and animation"""
    
    def setUp(self):
        """Set up test environment"""
        self.app = app.test_client()
        # Create and upload test audio file
        self.audio_file_path = self.create_test_audio_file()
        self.uploaded_filename = self.upload_audio_file()
        
    def create_test_audio_file(self, duration=3.0, sample_rate=16000):
        """Create a temporary audio file with speech-like patterns"""
        import numpy as np
        import tempfile
        import soundfile as sf
        
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        
        # Create a signal with pauses to better simulate speech patterns
        signal = np.zeros_like(t)
        
        # Add speech-like segments with pauses in between to simulate words
        # This creates 5 "words" with clear boundaries
        word_times = [(0.2, 0.5), (0.8, 1.1), (1.4, 1.7), (2.0, 2.3), (2.6, 2.9)]
        
        for start, end in word_times:
            mask = (t >= start) & (t < end)
            if np.any(mask):
                segment_t = t[mask] - start
                segment = 0.5 * np.sin(2 * np.pi * 440 * segment_t)
                signal[mask] = segment
        
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        sf.write(temp_file.name, signal, sample_rate)
        
        return temp_file.name
        
    def upload_audio_file(self):
        """Upload the test audio file and return the filename"""
        with open(self.audio_file_path, 'rb') as audio_file:
            response = self.app.post('/api/audio/upload', 
                data={'audio': (audio_file, 'test_sequence.wav')},
                content_type='multipart/form-data'
            )
        
        if response.status_code != 200:
            return None
            
        data = json.loads(response.data)
        return data['audio']['filename'] if data.get('success') else None
    
    def test_sync_marker_positions(self):
        """Test that timing markers are positioned correctly based on token times"""
        # This is more of an API test since we can't easily test browser playback
        # We'll test the API that provides timing marker positions
        
        # Create a mock alignment result with known timing
        alignment = {
            'tokens': [
                {'type': 'word', 'text': 'one', 'start_ms': 200, 'end_ms': 500},
                {'type': 'gap', 'text': '', 'start_ms': 500, 'end_ms': 800},
                {'type': 'word', 'text': 'two', 'start_ms': 800, 'end_ms': 1100}
            ],
            'audio': {
                'duration_ms': 3000
            }
        }
        
        # Request marker positions
        response = self.app.post('/api/audio/markers',
            json={
                'alignment': alignment
            }
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('markers', data)
        
        markers = data['markers']
        self.assertEqual(len(markers), 2)  # One for each word (not gaps)
        
        # Check that marker positions are correctly calculated as percentages
        self.assertAlmostEqual(markers[0]['position'], 6.67, delta=0.1)  # 200/3000 * 100
        self.assertAlmostEqual(markers[1]['position'], 26.67, delta=0.1)  # 800/3000 * 100

    def test_build_sequence_from_audio_endpoint(self):
        """Test the build_sequence_from_audio endpoint with proper parameters"""
        # First make sure we have an audio file available
        if not self.uploaded_filename:
            self.skipTest("Audio file upload failed, skipping test")
            
        # Test the endpoint
        response = self.app.post('/api/sequence/build-from-audio',
                              json={
                                  'audio_filename': self.uploaded_filename,
                                  'text': 'Test audio sequence',
                                  'alignment_tokens': [
                                      {'type': 'word', 'text': 'Test', 'start_ms': 0, 'end_ms': 400},
                                      {'type': 'gap', 'text': '', 'start_ms': 400, 'end_ms': 500},
                                      {'type': 'word', 'text': 'audio', 'start_ms': 500, 'end_ms': 900},
                                      {'type': 'gap', 'text': '', 'start_ms': 900, 'end_ms': 1000},
                                      {'type': 'word', 'text': 'sequence', 'start_ms': 1000, 'end_ms': 1500}
                                  ]
                              })
        
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['success'])
        self.assertIn('sequence', data)
        self.assertGreater(len(data['sequence']), 0)
        
        # Check that audio timing is applied
        word_frames = [f for f in data['sequence'] if not f.get('is_pause')]
        for frame in word_frames:
            self.assertIn('audio_start', frame)
            self.assertIn('audio_end', frame)
            self.assertIn('source', frame)
            self.assertEqual(frame['source'], 'audio_alignment')
        
        # Check that gaps are properly converted to pauses
        gaps = [f for f in data['sequence'] if f.get('is_pause')]
        self.assertGreaterEqual(len(gaps), 2)  # We should have at least 2 gaps
        for gap in gaps:
            self.assertIn('audio_start', gap)
            self.assertIn('audio_end', gap)
            self.assertEqual(gap['source'], 'audio_gap')
            
    def test_missing_parameters_in_build_from_audio(self):
        """Test error handling for missing parameters"""
        # Test with missing audio_filename
        response = self.app.post('/api/sequence/build-from-audio',
                              json={
                                  'text': 'Test',
                                  'alignment_tokens': []
                              })
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('error_info', data)
        
        # Test with missing alignment_tokens
        response = self.app.post('/api/sequence/build-from-audio',
                              json={
                                  'audio_filename': self.uploaded_filename if hasattr(self, 'uploaded_filename') else 'test.wav',
                                  'text': 'Test'
                              })
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        
    def test_nonexistent_audio_file(self):
        """Test error handling for nonexistent audio file"""
        response = self.app.post('/api/sequence/build-from-audio',
                              json={
                                  'audio_filename': 'nonexistent_file.wav',
                                  'text': 'Test',
                                  'alignment_tokens': [
                                      {'type': 'word', 'text': 'Test', 'start_ms': 0, 'end_ms': 100}
                                  ]
                              })
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data['success'])

def run_tests():
    """Run all sequence building tests"""
    unittest.main(argv=['first-arg-is-ignored'], exit=False)

if __name__ == '__main__':
    print("Running sequence building tests...")
    run_tests()
    print("All sequence building tests completed.")