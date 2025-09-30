#!/usr/bin/env python3
"""
Simple Phase 4 Test - Basic Functionality Validation
Validates core Phase 4 functionality without complex dependencies.
"""

import os
import sys
import json
import tempfile
import unittest
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_social_media_presets():
    """Test that social media presets are properly defined."""
    try:
        from social_media_exporter import SOCIAL_MEDIA_PRESETS
        
        expected_presets = [
            'instagram_story', 'instagram_reel', 'tiktok', 'youtube_shorts',
            'twitter_video', 'linkedin_video', 'facebook_video', 'square_1080'
        ]
        
        print("📱 Testing Social Media Presets...")
        
        for preset_name in expected_presets:
            assert preset_name in SOCIAL_MEDIA_PRESETS, f"Missing preset: {preset_name}"
            
            preset = SOCIAL_MEDIA_PRESETS[preset_name]
            assert preset.width > 0, f"Invalid width for {preset_name}"
            assert preset.height > 0, f"Invalid height for {preset_name}"
            assert preset.max_duration > 0, f"Invalid duration for {preset_name}"
            
            print(f"  ✅ {preset_name}: {preset.width}x{preset.height}, max {preset.max_duration}s")
        
        print(f"✅ All {len(expected_presets)} presets validated successfully!\n")
        return True
        
    except Exception as e:
        print(f"❌ Preset test failed: {e}")
        return False

def test_subtitle_segment_creation():
    """Test SubtitleSegment creation and properties."""
    try:
        from enhanced_subtitle_engine import SubtitleSegment
        
        print("📝 Testing Subtitle Segments...")
        
        # Create test segment
        segment = SubtitleSegment(
            id="test_seg",
            text="This is a test subtitle segment.",
            start_time=0.0,
            end_time=3.0,
            confidence=0.95
        )
        
        assert segment.id == "test_seg"
        assert segment.text == "This is a test subtitle segment."
        assert segment.start_time == 0.0
        assert segment.end_time == 3.0
        assert segment.confidence == 0.95
        assert segment.duration == 3.0
        assert segment.word_count == 6
        
        print(f"  ✅ Segment created: {segment.word_count} words, {segment.duration}s duration")
        print(f"✅ Subtitle segment creation validated!\n")
        return True
        
    except Exception as e:
        print(f"❌ Subtitle segment test failed: {e}")
        return False

def test_api_blueprint_structure():
    """Test that API blueprint is properly structured."""
    try:
        from phase4_export_endpoints import phase4_export_bp
        
        print("🌐 Testing API Blueprint Structure...")
        
        # Check blueprint properties
        assert hasattr(phase4_export_bp, 'name')
        assert hasattr(phase4_export_bp, 'url_prefix')
        assert phase4_export_bp.url_prefix == '/api/v4/export'
        
        # Check that blueprint has routes
        routes = list(phase4_export_bp.iter_rules())
        assert len(routes) > 0, "Blueprint has no routes"
        
        # Check for expected endpoints
        route_endpoints = [rule.endpoint.split('.')[-1] for rule in routes]
        expected_endpoints = [
            'get_social_media_presets',
            'export_video_with_subtitles', 
            'get_export_job_status',
            'validate_video_duration'
        ]
        
        for endpoint in expected_endpoints:
            assert endpoint in route_endpoints, f"Missing endpoint: {endpoint}"
            print(f"  ✅ Endpoint found: {endpoint}")
        
        print(f"✅ API blueprint structure validated ({len(routes)} routes)!\n")
        return True
        
    except Exception as e:
        print(f"❌ API blueprint test failed: {e}")
        return False

def test_export_configuration():
    """Test export configuration and settings."""
    try:
        from social_media_exporter import SocialMediaExporter
        
        print("⚙️ Testing Export Configuration...")
        
        # Create exporter instance
        exporter = SocialMediaExporter()
        
        # Test preset retrieval
        presets = exporter.get_available_presets()
        assert len(presets) > 0, "No presets available"
        
        # Test specific preset
        instagram_preset = exporter.get_preset('instagram_reel')
        assert instagram_preset is not None, "Instagram preset not found"
        assert instagram_preset.width == 1080, "Incorrect Instagram width"
        assert instagram_preset.height == 1920, "Incorrect Instagram height"
        
        print(f"  ✅ {len(presets)} presets loaded")
        print(f"  ✅ Instagram Reel: {instagram_preset.width}x{instagram_preset.height}")
        print(f"✅ Export configuration validated!\n")
        return True
        
    except Exception as e:
        print(f"❌ Export configuration test failed: {e}")
        return False

def test_flask_integration():
    """Test Flask integration readiness."""
    try:
        print("🌶️ Testing Flask Integration...")
        
        # Check Flask availability
        import flask
        print(f"  ✅ Flask {flask.__version__} available")
        
        # Check blueprint registration function
        from phase4_export_endpoints import register_phase4_export_blueprint
        print(f"  ✅ Blueprint registration function available")
        
        # Test that we can create a test app
        from flask import Flask
        test_app = Flask(__name__)
        
        # Register blueprint
        register_phase4_export_blueprint(test_app)
        print(f"  ✅ Blueprint registered successfully")
        
        print(f"✅ Flask integration validated!\n")
        return True
        
    except Exception as e:
        print(f"❌ Flask integration test failed: {e}")
        return False

def run_comprehensive_test():
    """Run all Phase 4 validation tests."""
    print("🎬 Phase 4 Enhanced Export - Quick Validation Suite")
    print("=" * 60)
    
    tests = [
        ("Social Media Presets", test_social_media_presets),
        ("Subtitle Segments", test_subtitle_segment_creation),
        ("API Blueprint", test_api_blueprint_structure),
        ("Export Configuration", test_export_configuration),
        ("Flask Integration", test_flask_integration)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"🔬 Running: {test_name}")
        print("-" * 30)
        
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("📋 Test Results Summary")
    print("=" * 30)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:25} {status}")
    
    success_rate = (passed / total) * 100 if total > 0 else 0
    print(f"\n📊 Success Rate: {passed}/{total} ({success_rate:.1f}%)")
    
    if passed == total:
        print("\n🎉 All Phase 4 core functionality tests passed!")
        print("✅ Enhanced social media export system is ready!")
        return True
    else:
        print(f"\n⚠️ {total - passed} test(s) failed. Please review the output above.")
        return False

if __name__ == '__main__':
    success = run_comprehensive_test()
    sys.exit(0 if success else 1)