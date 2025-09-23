"""
Load testing for Face Sequencer Pro using Locust
This tests the performance of the API endpoints under heavy load
"""

import os
import json
import random
from locust import HttpUser, task, between

class FaceSequencerUser(HttpUser):
    """Simulated user for load testing"""
    
    # Wait between 1 and 5 seconds between tasks
    wait_time = between(1, 5)
    
    def on_start(self):
        """Setup before starting tests"""
        # Create a test text for sequencing
        self.test_text = "The quick brown fox jumps over the lazy dog"
        
        # Prepare test data for API calls
        self.api_data = {
            "text": self.test_text,
            "timing_mode": "manual",
            "frame_duration": 80,
            "pause_duration": 120
        }
        
        # Check if audio system is available
        with self.client.get("/api/audio/status", catch_response=True) as response:
            if response.status_code == 200:
                result = response.json()
                self.audio_available = result.get('available', False)
            else:
                self.audio_available = False
    
    @task(3)
    def view_home_page(self):
        """Visit the home page - highest frequency task"""
        self.client.get("/")
    
    @task(2)
    def build_sequence(self):
        """Build a text sequence - medium frequency task"""
        self.client.post("/api/sequence/build", json=self.api_data)
    
    @task(1)
    def export_sequence(self):
        """Export a sequence as JSON - lower frequency task"""
        # First build a sequence
        response = self.client.post("/api/sequence/build", json=self.api_data)
        
        if response.status_code == 200:
            # Then export it
            export_data = {
                "filename": f"test_export_{random.randint(1000, 9999)}.json"
            }
            self.client.post("/api/export/json", json=export_data)
    
    @task(1)
    def analyze_audio(self):
        """Test audio analysis endpoint - only if audio is available"""
        if not hasattr(self, 'audio_available') or not self.audio_available:
            return
        
        # Use one of the test audio files if available
        audio_files = ["1758577759_test.wav", "1758577763_test.wav"]
        selected_file = random.choice(audio_files)
        
        self.client.post("/api/audio/analyze", json={
            "audio_filename": selected_file
        })
    
    @task
    def get_sequence_preview(self):
        """Get preview frame for a sequence"""
        # First build a sequence
        response = self.client.post("/api/sequence/build", json=self.api_data)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success') and len(result.get('sequence', [])) > 0:
                # Get a random frame to preview
                frame_index = random.randint(0, len(result['sequence']) - 1)
                self.client.get(f"/api/sequence/preview/{frame_index}")


class AudioLoadTesting(HttpUser):
    """Specific user class for audio processing load testing"""
    
    # Audio processing is slower, so wait longer between requests
    wait_time = between(5, 15)
    
    def on_start(self):
        """Check if audio system is available before starting"""
        with self.client.get("/api/audio/status", catch_response=True) as response:
            if response.status_code == 200:
                result = response.json()
                self.audio_available = result.get('available', False)
            else:
                self.audio_available = False
    
    @task
    def build_sequence_from_audio(self):
        """Test building sequence from audio alignment results"""
        if not hasattr(self, 'audio_available') or not self.audio_available:
            return
            
        # Use test audio files
        audio_files = ["1758577759_test.wav", "1758577763_test.wav"]
        selected_file = random.choice(audio_files)
        
        # Generate alignment tokens for testing
        tokens = []
        current_time = 0
        test_text = "This is a test for audio alignment sequence building"
        
        # Create simulated tokens for each word
        for word in test_text.split():
            word_duration = len(word) * 80  # 80ms per character
            tokens.append({
                "type": "word",
                "text": word,
                "start_ms": current_time,
                "end_ms": current_time + word_duration
            })
            current_time += word_duration
            
            # Add gaps between words (50-200ms)
            gap_duration = random.randint(50, 200)
            tokens.append({
                "type": "gap",
                "text": "",
                "start_ms": current_time,
                "end_ms": current_time + gap_duration
            })
            current_time += gap_duration
        
        # Build sequence from audio
        self.client.post("/api/sequence/build-from-audio", json={
            "audio_filename": selected_file,
            "text": test_text,
            "alignment_tokens": tokens
        })


# To run this test:
# locust -f locustfile.py --host=http://localhost:5000
#
# Then open http://localhost:8089 in your browser to control the test