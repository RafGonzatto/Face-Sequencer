#!/usr/bin/env python3
"""
Phase 4 Test Suite - Enhanced Social Media Export Validation
Comprehensive testing for social media export system, subtitle burn-in, and platform optimization.
"""

import os
import sys
import json
import asyncio
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
import unittest
from unittest.mock import Mock, patch, MagicMock

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import Phase 4 components
try:
    from social_media_exporter import SocialMediaExporter, SocialMediaPreset
    from enhanced_subtitle_engine import SubtitleSegment
    from phase4_export_endpoints import phase4_export_bp
    from app import app
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure all Phase 4 dependencies are installed")
    sys.exit(1)

class TestSocialMediaExporter(unittest.TestCase):
    """Test suite for the SocialMediaExporter class."""
    
    def setUp(self):
        """Set up test environment."""
        self.exporter = SocialMediaExporter()
        self.test_dir = tempfile.mkdtemp()
        
        # Create sample subtitle segments
        self.sample_segments = [
            SubtitleSegment(
                id="seg1",
                text="Hello world, this is a test subtitle segment.",
                start_time=0.0,
                end_time=3.0,
                confidence=0.95
            ),
            SubtitleSegment(
                id="seg2", 
                text="This is the second segment with more text to test wrapping.",
                start_time=3.0,
                end_time=6.5,
                confidence=0.88
            ),
            SubtitleSegment(
                id="seg3",
                text="Final segment!",
                start_time=6.5,
                end_time=8.0,
                confidence=0.92
            )
        ]
    
    def tearDown(self):
        """Clean up test environment."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_preset_availability(self):
        """Test that all expected presets are available."""
        presets = self.exporter.get_available_presets()
        
        expected_presets = [
            'instagram_story', 'instagram_reel', 'tiktok', 'youtube_shorts',
            'twitter_video', 'linkedin_video', 'facebook_video', 'square_1080'
        ]
        
        for preset_name in expected_presets:
            self.assertIn(preset_name, presets, f"Missing preset: {preset_name}")
            
        print(f"✅ All {len(expected_presets)} presets available")
    
    def test_preset_validation(self):
        """Test preset configuration validation."""
        for preset_name, preset in self.exporter.get_available_presets().items():
            # Validate required fields
            self.assertIsInstance(preset.width, int)
            self.assertIsInstance(preset.height, int)
            self.assertGreater(preset.width, 0)
            self.assertGreater(preset.height, 0)
            
            # Validate duration limits
            self.assertGreater(preset.max_duration, 0)
            self.assertLessEqual(preset.max_duration, 3600)  # Max 1 hour
            
            # Validate subtitle constraints
            self.assertGreater(preset.max_chars_per_line, 0)
            self.assertGreater(preset.max_lines, 0)
            self.assertGreater(preset.reading_speed_wps, 0)
            
        print(f"✅ All preset configurations validated")
    
    def test_subtitle_optimization(self):
        """Test subtitle optimization for different platforms."""
        preset = self.exporter.get_preset('instagram_story')
        optimized = self.exporter._optimize_subtitles_for_preset(
            self.sample_segments, preset, {}
        )
        
        self.assertEqual(len(optimized), len(self.sample_segments))
        
        for segment in optimized:
            # Check character limits
            for line in segment.text.split('\n'):
                self.assertLessEqual(
                    len(line), preset.max_chars_per_line,
                    f"Line too long: '{line}' ({len(line)} chars)"
                )
            
            # Check line limits
            lines = segment.text.split('\n')
            self.assertLessEqual(
                len(lines), preset.max_lines,
                f"Too many lines: {len(lines)}"
            )
        
        print(f"✅ Subtitle optimization working correctly")
    
    def test_ass_generation(self):
        """Test ASS subtitle file generation."""
        preset = self.exporter.get_preset('tiktok')
        ass_content = self.exporter._create_ass_subtitle_file(
            self.sample_segments, preset
        )
        
        # Check ASS format structure
        self.assertIn('[Script Info]', ass_content)
        self.assertIn('[V4+ Styles]', ass_content)
        self.assertIn('[Events]', ass_content)
        self.assertIn('Dialogue:', ass_content)
        
        # Check timing format
        lines = ass_content.split('\n')
        dialogue_lines = [line for line in lines if line.startswith('Dialogue:')]
        self.assertGreater(len(dialogue_lines), 0)
        
        print(f"✅ ASS subtitle generation working")
    
    @patch('subprocess.run')
    def test_ffmpeg_command_generation(self, mock_run):
        """Test FFmpeg command generation for different presets."""
        mock_run.return_value = Mock(returncode=0, stdout=b'', stderr=b'')
        
        test_input = os.path.join(self.test_dir, 'input.mp4')
        test_output = os.path.join(self.test_dir, 'output.mp4')
        
        # Create dummy input file
        Path(test_input).touch()
        
        preset = self.exporter.get_preset('youtube_shorts')
        
        # Test command generation
        asyncio.run(self.exporter._run_ffmpeg_export(
            job_id="test_job",
            input_path=test_input,
            output_path=test_output,
            subtitle_segments=self.sample_segments,
            preset=preset,
            custom_settings={}
        ))
        
        # Verify FFmpeg was called
        self.assertTrue(mock_run.called)
        
        # Check command structure
        called_args = mock_run.call_args[0][0]
        self.assertEqual(called_args[0], 'ffmpeg')
        self.assertIn('-i', called_args)
        self.assertIn('-vf', called_args)
        
        print(f"✅ FFmpeg command generation working")

class TestPhase4APIEndpoints(unittest.TestCase):
    """Test suite for Phase 4 API endpoints."""
    
    def setUp(self):
        """Set up test client."""
        app.config['TESTING'] = True
        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()
        # Ensure blueprint registered (some dynamic import paths may skip original registration block)
        if 'phase4_export' not in app.blueprints:
            try:
                from phase4_export_endpoints import register_phase4_export_blueprint
                register_phase4_export_blueprint(app)
            except Exception as _e:  # noqa: BLE001
                print(f"Warning: failed to register phase4 blueprint in test setup: {_e}")
    
    def tearDown(self):
        """Clean up test environment."""
        self.app_context.pop()
    
    def test_get_presets(self):
        """Test GET /api/v4/export/presets endpoint."""
        response = self.client.get('/api/v4/export/presets')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('presets', data['data'])
        self.assertGreater(data['data']['total_presets'], 0)
        
        print(f"✅ Presets API endpoint working")
    
    def test_get_preset_details(self):
        """Test GET /api/v4/export/presets/{name} endpoint."""
        response = self.client.get('/api/v4/export/presets/instagram_reel')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('preset', data['data'])
        
        preset = data['data']['preset']
        self.assertEqual(preset['width'], 1080)
        self.assertEqual(preset['height'], 1920)
        
        print(f"✅ Preset details API endpoint working")
    
    def test_preset_recommendations(self):
        """Test POST /api/v4/export/presets/recommendations endpoint."""
        request_data = {
            'content_type': 'casual',
            'duration': 30,
            'target_audience': 'young'
        }
        
        response = self.client.post(
            '/api/v4/export/presets/recommendations',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('recommendations', data['data'])
        
        print(f"✅ Preset recommendations API endpoint working")
    
    def test_duration_validation(self):
        """Test POST /api/v4/export/validate-duration endpoint."""
        request_data = {
            'duration': 45,
            'platforms': ['instagram_reel', 'tiktok', 'youtube_shorts']
        }
        
        response = self.client.post(
            '/api/v4/export/validate-duration',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('platform_results', data['data'])
        
        # Check validation results
        for platform, result in data['data']['platform_results'].items():
            self.assertIn('valid', result)
            self.assertIn('max_duration', result)
        
        print(f"✅ Duration validation API endpoint working")
    
    def test_platform_optimization(self):
        """Test POST /api/v4/export/optimize-for-platform endpoint."""
        subtitle_data = [
            {
                'id': 'seg1',
                'text': 'This is a very long subtitle that needs to be optimized for the platform',
                'start_time': 0.0,
                'end_time': 3.0,
                'confidence': 0.95
            }
        ]
        
        request_data = {
            'platform': 'instagram',
            'subtitle_segments': subtitle_data,
            'custom_constraints': {}
        }
        
        response = self.client.post(
            '/api/v4/export/optimize-for-platform',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('optimized_segments', data['data'])
        self.assertIn('optimization_stats', data['data'])
        
        print(f"✅ Platform optimization API endpoint working")

class TestPhase4Integration(unittest.TestCase):
    """Integration tests for Phase 4 components."""
    
    def setUp(self):
        """Set up integration test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.exporter = SocialMediaExporter()
    
    def tearDown(self):
        """Clean up integration test environment."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_end_to_end_workflow(self):
        """Test complete export workflow simulation."""
        # Create test subtitle segments
        segments = [
            SubtitleSegment(
                id="test1",
                text="Welcome to our amazing content!",
                start_time=0.0,
                end_time=2.5,
                confidence=0.95
            ),
            SubtitleSegment(
                id="test2",
                text="This video was created with our Phase 4 export system.",
                start_time=2.5,
                end_time=6.0,
                confidence=0.92
            )
        ]
        
        # Test preset selection
        preset = self.exporter.get_preset('instagram_story')
        self.assertIsNotNone(preset)
        
        # Test subtitle optimization
        optimized = self.exporter._optimize_subtitles_for_preset(segments, preset, {})
        self.assertEqual(len(optimized), 2)
        
        # Test ASS file generation
        ass_content = self.exporter._create_ass_subtitle_file(optimized, preset)
        self.assertIn('[Events]', ass_content)
        
        print(f"✅ End-to-end workflow simulation successful")
    
    def test_batch_processing_simulation(self):
        """Test batch processing capabilities."""
        platforms = ['instagram_reel', 'tiktok', 'youtube_shorts']
        
        for platform in platforms:
            preset = self.exporter.get_preset(platform)
            self.assertIsNotNone(preset, f"Missing preset for {platform}")
            
            # Validate preset specifications match platform requirements
            if platform == 'instagram_reel':
                self.assertEqual(preset.width, 1080)
                self.assertEqual(preset.height, 1920)
                self.assertLessEqual(preset.max_duration, 90)
        
        print(f"✅ Batch processing simulation successful")

def run_performance_benchmarks():
    """Run performance benchmarks for Phase 4 components."""
    print("\n🚀 Running Phase 4 Performance Benchmarks...")
    
    exporter = SocialMediaExporter()
    
    # Benchmark preset loading
    start_time = datetime.now()
    presets = exporter.get_available_presets()
    preset_load_time = (datetime.now() - start_time).total_seconds()
    
    print(f"📊 Preset Loading: {preset_load_time*1000:.2f}ms for {len(presets)} presets")
    
    # Benchmark subtitle optimization
    test_segments = [
        SubtitleSegment(f"seg{i}", f"Test segment {i} with sample text content", i*2.0, (i+1)*2.0, 0.9)
        for i in range(100)
    ]
    
    start_time = datetime.now()
    preset = exporter.get_preset('instagram_reel')
    optimized = exporter._optimize_subtitles_for_preset(test_segments, preset, {})
    optimization_time = (datetime.now() - start_time).total_seconds()
    
    print(f"📊 Subtitle Optimization: {optimization_time*1000:.2f}ms for {len(test_segments)} segments")
    
    # Benchmark ASS generation
    start_time = datetime.now()
    ass_content = exporter._create_ass_subtitle_file(optimized, preset)
    ass_generation_time = (datetime.now() - start_time).total_seconds()
    
    print(f"📊 ASS Generation: {ass_generation_time*1000:.2f}ms for {len(ass_content)} characters")
    
    return {
        'preset_load_time': preset_load_time,
        'optimization_time': optimization_time,
        'ass_generation_time': ass_generation_time
    }

def main():
    """Run comprehensive Phase 4 test suite."""
    print("🎬 Phase 4 Enhanced Export Test Suite")
    print("=" * 50)
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_suite.addTest(unittest.makeSuite(TestSocialMediaExporter))
    test_suite.addTest(unittest.makeSuite(TestPhase4APIEndpoints))
    test_suite.addTest(unittest.makeSuite(TestPhase4Integration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Run performance benchmarks
    benchmarks = run_performance_benchmarks()
    
    # Summary report
    print("\n📋 Phase 4 Test Summary")
    print("=" * 30)
    print(f"Tests Run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success Rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    print("\n⚡ Performance Summary")
    print("=" * 20)
    print(f"Preset Loading: {benchmarks['preset_load_time']*1000:.1f}ms")
    print(f"Optimization: {benchmarks['optimization_time']*1000:.1f}ms")
    print(f"ASS Generation: {benchmarks['ass_generation_time']*1000:.1f}ms")
    
    all_passed = not (result.failures or result.errors)
    if not all_passed:
        print("\n❌ Some tests failed. Please review the output above.")
    else:
        print("\n🎉 All Phase 4 tests passed successfully!")
        print("✅ Enhanced social media export system is ready for production use.")
    return all_passed

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)