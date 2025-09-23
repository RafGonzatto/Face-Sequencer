"""
End-to-End Test for Video Export Flow

This script tests the complete video export flow to ensure it works correctly.
It creates a simple sequence, exports it to MP4, and verifies the result.
"""
import os
import sys
import time
import unittest
from PIL import Image
import numpy as np

# Add the current directory to the path so we can import our modules
sys.path.insert(0, os.path.abspath('.'))

# Import our modules
from lipanim_core_demo import export_mp4, build_sequence, load_letter_map_from_dir

class TestExportFlow(unittest.TestCase):
    """Test the end-to-end export flow"""
    
    def setUp(self):
        """Set up test environment"""
        # Create a test directory
        self.test_dir = os.path.abspath("test_export")
        os.makedirs(self.test_dir, exist_ok=True)
        
        # Create test frames - small colored squares
        self.create_test_frames()
        
        # Create a simple test sequence
        self.letter_map = {
            'A': os.path.join(self.test_dir, "frame_red.png"),
            'B': os.path.join(self.test_dir, "frame_green.png"),
            'C': os.path.join(self.test_dir, "frame_blue.png")
        }
        
        # Output path for the test video
        self.output_path = os.path.join(self.test_dir, "test_output.mp4")
        
        # If the output file already exists, remove it
        if os.path.exists(self.output_path):
            os.remove(self.output_path)
            
    def create_test_frames(self):
        """Create test frames for the video"""
        # Create 50x50 colored frames
        colors = {
            "red": (255, 0, 0),
            "green": (0, 255, 0),
            "blue": (0, 0, 255)
        }
        
        for color_name, rgb in colors.items():
            # Create a 50x50 colored image
            img = Image.new('RGB', (50, 50), color=rgb)
            img_path = os.path.join(self.test_dir, f"frame_{color_name}.png")
            img.save(img_path)
            print(f"Created test frame: {img_path}")
    
    def test_export_flow(self):
        """Test the complete export flow"""
        print("\n=== Testing Export Flow ===")
        
        # 1. Build a sequence with our test frames
        sequence = build_sequence("ABC", self.letter_map, dur_ms=500, gap_ms=0)
        self.assertTrue(len(sequence) == 3, "Sequence should have 3 frames")
        print(f"Created test sequence with {len(sequence)} frames")
        
        # Print sequence details for debugging
        for i, frame in enumerate(sequence):
            print(f"Frame {i}: char={frame['char']}, img={os.path.basename(frame['img'])}, duration={frame['ms']}ms")
        
        # 2. Export the sequence to MP4
        print("\nExporting sequence to MP4...")
        
        # Capture progress updates
        progress_updates = []
        def progress_callback(progress, message=None):
            progress_updates.append((progress, message))
            print(f"Export progress: {progress}% - {message}")
        
        # Check exact parameters being passed
        print("\nExport parameters:")
        print(f"  Sequence length: {len(sequence)}")
        print(f"  Output path: {self.output_path}")
        print(f"  FPS: 2")  # 500ms per frame = 2 FPS
        print(f"  CRF: 23")  # Standard quality
        print(f"  Preset: medium")
        
        # Try export with detailed logging
        success = export_mp4(
            seq=sequence,
            path=self.output_path,
            fps=2,  # 500ms per frame = 2 FPS
            crf=23,  # Standard quality
            preset="medium",
            progress_callback=progress_callback
        )
        
        # 3. Verify the export was successful
        self.assertTrue(success, "Export should complete successfully")
        self.assertTrue(os.path.exists(self.output_path), "Output file should exist")
        self.assertTrue(os.path.getsize(self.output_path) > 0, "Output file should not be empty")
        
        # Print final information
        print(f"\nExport successful: {success}")
        print(f"Output file: {self.output_path}")
        print(f"File size: {os.path.getsize(self.output_path)} bytes")
        print(f"Received {len(progress_updates)} progress updates")
        
        # Print the last progress message
        if progress_updates:
            last_progress = progress_updates[-1]
            print(f"Final progress: {last_progress[0]}% - {last_progress[1]}")
    
    def tearDown(self):
        """Clean up test environment"""
        # We'll leave the test files for inspection
        pass

if __name__ == "__main__":
    unittest.main()