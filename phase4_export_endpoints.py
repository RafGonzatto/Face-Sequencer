"""
Phase 4 Export API Endpoints - Enhanced Social Media Export
Advanced video export with subtitle burn-in and social media optimization.
"""

from flask import Blueprint, request, jsonify, send_file
import asyncio
import uuid
import os
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from social_media_exporter import SocialMediaExporter, SocialMediaPreset
from enhanced_subtitle_engine import SubtitleSegment
from api_responses import success_response, error_response

logger = logging.getLogger(__name__)

# Create Blueprint for Phase 4 export endpoints
phase4_export_bp = Blueprint('phase4_export', __name__, url_prefix='/api/v4/export')
phase4_export_bp = Blueprint('phase4_export', __name__, url_prefix='/api/v4/export')

# ---------------------------------------------------------------------------
# Blueprint helper: tests expect blueprint.iter_rules() to exist (Flask's
# actual Blueprint does not expose iter_rules). We emulate a minimal version
# that returns objects with an 'endpoint' attribute similar to app.url_map
# rules so tests can introspect available endpoints.
# ---------------------------------------------------------------------------
if not hasattr(phase4_export_bp, 'iter_rules'):
    phase4_export_bp._fs_registered_endpoints = []  # type: ignore[attr-defined]
    _orig_route = phase4_export_bp.route

    def _tracking_route(rule, **options):  # type: ignore
        def decorator(f):
            endpoint = options.get('endpoint', f.__name__)
            # Store fully qualified endpoint like Flask would (blueprint.name.func)
            fq_endpoint = f"{phase4_export_bp.name}.{endpoint}"
            phase4_export_bp._fs_registered_endpoints.append(fq_endpoint)  # type: ignore
            return _orig_route(rule, **options)(f)
        return decorator

    phase4_export_bp.route = _tracking_route  # type: ignore

    def iter_rules():  # type: ignore
        class _RuleProxy:
            def __init__(self, endpoint):
                self.endpoint = endpoint
        return [_RuleProxy(ep) for ep in getattr(phase4_export_bp, '_fs_registered_endpoints', [])]

    phase4_export_bp.iter_rules = iter_rules  # type: ignore

# Initialize social media exporter
social_exporter = SocialMediaExporter()

# =============================================================================
# Social Media Preset Management
# =============================================================================

@phase4_export_bp.route('/presets', methods=['GET'])
def get_social_media_presets():
    """Get all available social media export presets."""
    try:
        presets = social_exporter.get_available_presets()
        
        return success_response(
            'Presets retrieved',
            data={
                'presets': presets,
                'total_presets': len(presets),
                'preset_names': list(presets.keys())
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to get presets: {e}")
        return error_response("Failed to retrieve presets", 500)

@phase4_export_bp.route('/presets/<preset_name>', methods=['GET'])
def get_preset_details(preset_name):
    """Get details of a specific preset."""
    try:
        preset = social_exporter.get_preset(preset_name)
        
        if not preset:
            return error_response(f"Preset not found: {preset_name}", 404)
        
        return success_response(
            'Preset details retrieved',
            data={
                'preset': preset.to_dict(),
                'preset_name': preset_name
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to get preset {preset_name}: {e}")
        return error_response("Failed to retrieve preset details", 500)

@phase4_export_bp.route('/presets/recommendations', methods=['POST'])
def get_preset_recommendations():
    """Get preset recommendations based on content analysis."""
    try:
        data = request.get_json()
        
        content_type = data.get('content_type', 'general')  # story, reel, video, etc.
        duration = data.get('duration', 30)  # seconds
        audience = data.get('target_audience', 'general')  # young, professional, etc.
        
        recommendations = []
        
        # Recommend based on duration
        if duration <= 15:
            recommendations.extend(['instagram_story', 'tiktok'])
        elif duration <= 60:
            recommendations.extend(['instagram_reel', 'tiktok', 'youtube_shorts'])
        elif duration <= 140:
            recommendations.extend(['twitter_video', 'linkedin_video'])
        else:
            recommendations.extend(['facebook_video', 'linkedin_video'])
        
        # Filter based on content type
        if content_type == 'professional':
            recommendations = [p for p in recommendations if 'linkedin' in p or 'facebook' in p]
        elif content_type == 'casual':
            recommendations = [p for p in recommendations if any(platform in p for platform in ['tiktok', 'instagram'])]
        
        # Get preset details for recommendations
        recommended_presets = {}
        for preset_name in recommendations[:3]:  # Top 3 recommendations
            preset = social_exporter.get_preset(preset_name)
            if preset:
                recommended_presets[preset_name] = preset.to_dict()
        
        return success_response(
            'Recommendations generated',
            data={
                'recommendations': recommended_presets,
                'analysis': {
                    'content_type': content_type,
                    'duration': duration,
                    'target_audience': audience
                }
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to get recommendations: {e}")
        return error_response("Failed to generate recommendations", 500)

# =============================================================================
# Enhanced Video Export
# =============================================================================

@phase4_export_bp.route('/video-with-subtitles', methods=['POST'])
async def export_video_with_subtitles():
    """Export video with burned-in subtitles optimized for social media."""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['input_video_path', 'subtitle_segments', 'output_filename']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return error_response(f"Missing required fields: {', '.join(missing_fields)}", 400)
        
        input_video_path = data['input_video_path']
        subtitle_segments_data = data['subtitle_segments']
        output_filename = data['output_filename']
        preset_name = data.get('preset_name', 'instagram_reel')
        custom_settings = data.get('custom_settings', {})
        
        # Validate input video exists
        if not os.path.exists(input_video_path):
            return error_response("Input video file not found", 404)
        
        # Convert subtitle data to SubtitleSegment objects
        subtitle_segments = []
        for seg_data in subtitle_segments_data:
            try:
                segment = SubtitleSegment(
                    id=seg_data.get('id', str(uuid.uuid4())),
                    text=seg_data['text'],
                    start_time=float(seg_data['start_time']),
                    end_time=float(seg_data['end_time']),
                    confidence=float(seg_data.get('confidence', 1.0))
                )
                subtitle_segments.append(segment)
            except (KeyError, ValueError) as e:
                return error_response(f"Invalid subtitle segment data: {e}", 400)
        
        if not subtitle_segments:
            return error_response("No valid subtitle segments provided", 400)
        
        # Generate job ID and output path
        job_id = str(uuid.uuid4())
        
        # Ensure output filename has proper extension
        if not output_filename.lower().endswith('.mp4'):
            output_filename += '.mp4'
        
        # Create output directory if needed
        output_dir = data.get('output_directory', 'exports')
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, output_filename)
        
        # Start export job
        export_result = await social_exporter.export_with_subtitles(
            job_id=job_id,
            input_video_path=input_video_path,
            subtitle_segments=subtitle_segments,
            output_path=output_path,
            preset_name=preset_name,
            custom_settings=custom_settings
        )
        
        if export_result['success']:
            return success_response({
                'job_id': job_id,
                'output_path': output_path,
                'output_filename': output_filename,
                'file_size_mb': export_result['file_size_mb'],
                'processing_time': export_result['processing_time'],
                'preset_used': preset_name,
                'subtitle_count': len(subtitle_segments),
                'download_url': f"/api/v4/export/download/{job_id}"
            })
        else:
            return error_response(export_result['error'], 500)
        
    except Exception as e:
        logger.error(f"Video export with subtitles failed: {e}")
        return error_response("Export failed", 500)

@phase4_export_bp.route('/batch-export', methods=['POST'])
async def batch_export_videos():
    """Export multiple videos with different presets."""
    try:
        data = request.get_json()
        
        export_jobs = data.get('export_jobs', [])
        if not export_jobs:
            return error_response("No export jobs provided", 400)
        
        # Validate each job
        for i, job_data in enumerate(export_jobs):
            required_fields = ['input_video_path', 'subtitle_segments', 'output_filename']
            missing_fields = [field for field in required_fields if field not in job_data]
            if missing_fields:
                return error_response(f"Job {i}: Missing fields: {', '.join(missing_fields)}", 400)
        
        # Start batch export
        batch_id = str(uuid.uuid4())
        job_results = []
        
        for i, job_data in enumerate(export_jobs):
            try:
                # Convert subtitle data
                subtitle_segments = []
                for seg_data in job_data['subtitle_segments']:
                    segment = SubtitleSegment(
                        id=seg_data.get('id', str(uuid.uuid4())),
                        text=seg_data['text'],
                        start_time=float(seg_data['start_time']),
                        end_time=float(seg_data['end_time']),
                        confidence=float(seg_data.get('confidence', 1.0))
                    )
                    subtitle_segments.append(segment)
                
                # Generate paths
                job_id = f"{batch_id}_{i}"
                output_dir = job_data.get('output_directory', 'exports/batch')
                os.makedirs(output_dir, exist_ok=True)
                
                output_filename = job_data['output_filename']
                if not output_filename.lower().endswith('.mp4'):
                    output_filename += '.mp4'
                
                output_path = os.path.join(output_dir, output_filename)
                
                # Start export
                export_result = await social_exporter.export_with_subtitles(
                    job_id=job_id,
                    input_video_path=job_data['input_video_path'],
                    subtitle_segments=subtitle_segments,
                    output_path=output_path,
                    preset_name=job_data.get('preset_name', 'instagram_reel'),
                    custom_settings=job_data.get('custom_settings', {})
                )
                
                job_results.append({
                    'job_index': i,
                    'job_id': job_id,
                    'success': export_result['success'],
                    'output_path': output_path if export_result['success'] else None,
                    'error': export_result.get('error'),
                    'processing_time': export_result.get('processing_time', 0)
                })
                
            except Exception as e:
                job_results.append({
                    'job_index': i,
                    'job_id': f"{batch_id}_{i}",
                    'success': False,
                    'error': str(e)
                })
        
        # Calculate batch statistics
        successful_jobs = sum(1 for result in job_results if result['success'])
        total_processing_time = sum(result.get('processing_time', 0) for result in job_results)
        
        return success_response({
            'batch_id': batch_id,
            'total_jobs': len(export_jobs),
            'successful_jobs': successful_jobs,
            'failed_jobs': len(export_jobs) - successful_jobs,
            'total_processing_time': total_processing_time,
            'job_results': job_results
        })
        
    except Exception as e:
        logger.error(f"Batch export failed: {e}")
        return error_response("Batch export failed", 500)

@phase4_export_bp.route('/job-status/<job_id>', methods=['GET'])
def get_export_job_status(job_id):
    """Get status of an export job."""
    try:
        job_status = social_exporter.get_job_status(job_id)
        
        if not job_status:
            return error_response("Job not found", 404)
        
        return success_response({
            'job_status': job_status
        })
        
    except Exception as e:
        logger.error(f"Failed to get job status for {job_id}: {e}")
        return error_response("Failed to get job status", 500)

@phase4_export_bp.route('/download/<job_id>', methods=['GET'])
def download_exported_video(job_id):
    """Download exported video file."""
    try:
        job_status = social_exporter.get_job_status(job_id)
        
        if not job_status:
            return error_response("Job not found", 404)
        
        if job_status['status'] != 'completed':
            return error_response(f"Job not completed. Status: {job_status['status']}", 400)
        
        # Find the output file (this would need to be stored in job data)
        # For now, return a placeholder response
        return success_response({
            'download_ready': True,
            'job_id': job_id,
            'message': 'File ready for download',
            'file_size': job_status.get('output_file_size', 0)
        })
        
    except Exception as e:
        logger.error(f"Failed to prepare download for {job_id}: {e}")
        return error_response("Download preparation failed", 500)

# =============================================================================
# Platform-Specific Optimization
# =============================================================================

@phase4_export_bp.route('/optimize-for-platform', methods=['POST'])
def optimize_subtitles_for_platform():
    """Optimize subtitles for a specific social media platform."""
    try:
        data = request.get_json()
        
        platform = data.get('platform', 'instagram')
        subtitle_segments_data = data.get('subtitle_segments', [])
        custom_constraints = data.get('custom_constraints', {})
        
        if not subtitle_segments_data:
            return error_response("No subtitle segments provided", 400)
        
        # Get platform preset
        preset_map = {
            'instagram_story': 'instagram_story',
            'instagram_reel': 'instagram_reel',
            'instagram': 'instagram_reel',
            'tiktok': 'tiktok',
            'youtube_shorts': 'youtube_shorts',
            'youtube': 'youtube_shorts',
            'twitter': 'twitter_video',
            'linkedin': 'linkedin_video',
            'facebook': 'facebook_video'
        }
        
        preset_name = preset_map.get(platform, 'instagram_reel')
        preset = social_exporter.get_preset(preset_name)
        
        if not preset:
            return error_response(f"No preset found for platform: {platform}", 400)
        
        # Convert and optimize subtitle segments
        optimized_segments = []
        
        for seg_data in subtitle_segments_data:
            try:
                # Create original segment
                segment = SubtitleSegment(
                    id=seg_data.get('id', str(uuid.uuid4())),
                    text=seg_data['text'],
                    start_time=float(seg_data['start_time']),
                    end_time=float(seg_data['end_time']),
                    confidence=float(seg_data.get('confidence', 1.0))
                )
                
                # Optimize for platform
                optimized_segment = social_exporter._optimize_subtitles_for_preset(
                    [segment], preset, custom_constraints
                )[0]
                
                optimized_segments.append({
                    'id': optimized_segment.id,
                    'text': optimized_segment.text,
                    'start_time': optimized_segment.start_time,
                    'end_time': optimized_segment.end_time,
                    'confidence': optimized_segment.confidence,
                    'word_count': optimized_segment.word_count,
                    'reading_speed': optimized_segment.reading_speed,
                    'platform_optimized': optimized_segment.platform_optimized,
                    'changes_made': optimized_segment.text != segment.text
                })
                
            except (KeyError, ValueError) as e:
                logger.warning(f"Skipping invalid segment: {e}")
                continue
        
        # Calculate optimization statistics
        changes_made = sum(1 for seg in optimized_segments if seg['changes_made'])
        avg_reading_speed = sum(seg['reading_speed'] for seg in optimized_segments) / len(optimized_segments) if optimized_segments else 0
        
        return success_response(
            'Platform optimization complete',
            data={
                'optimized_segments': optimized_segments,
                'platform': platform,
                'preset_used': preset_name,
                'optimization_stats': {
                    'total_segments': len(optimized_segments),
                    'segments_modified': changes_made,
                    'modification_rate': changes_made / len(optimized_segments) if optimized_segments else 0,
                    'average_reading_speed': avg_reading_speed,
                    'preset_constraints': {
                        'max_chars_per_line': preset.max_chars_per_line,
                        'max_lines': preset.max_lines,
                        'target_reading_speed': preset.reading_speed_wps
                    }
                }
            }
        )
        
    except Exception as e:
        logger.error(f"Platform optimization failed: {e}")
        return error_response("Platform optimization failed", 500)

@phase4_export_bp.route('/validate-duration', methods=['POST'])
def validate_video_duration():
    """Validate video duration against platform limits."""
    try:
        data = request.get_json()
        
        duration = float(data.get('duration', 0))
        platforms = data.get('platforms', ['instagram_reel'])
        
        if duration <= 0:
            return error_response("Invalid duration", 400)
        
        validation_results = {}
        
        for platform in platforms:
            preset = social_exporter.get_preset(platform)
            if preset:
                is_valid = duration <= preset.max_duration
                validation_results[platform] = {
                    'valid': is_valid,
                    'max_duration': preset.max_duration,
                    'current_duration': duration,
                    'excess_duration': max(0, duration - preset.max_duration),
                    'platform_name': preset.name
                }
            else:
                validation_results[platform] = {
                    'valid': False,
                    'error': 'Unknown platform'
                }
        
        # Overall validation
        all_valid = all(result.get('valid', False) for result in validation_results.values())
        
        return success_response(
            'Duration validation results',
            data={
                'duration': duration,
                'overall_valid': all_valid,
                'platform_results': validation_results,
                'recommendations': [
                    f"Trim video by {max(result.get('excess_duration', 0) for result in validation_results.values()):.1f}s for universal compatibility"
                ] if not all_valid else []
            }
        )
        
    except Exception as e:
        logger.error(f"Duration validation failed: {e}")
        return error_response("Duration validation failed", 500)

# =============================================================================
# Export Statistics and Management
# =============================================================================

@phase4_export_bp.route('/statistics', methods=['GET'])
def get_export_statistics():
    """Get export performance statistics."""
    try:
        stats = social_exporter.get_export_statistics()
        
        return success_response({
            'export_statistics': stats,
            'generated_at': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Failed to get export statistics: {e}")
        return error_response("Failed to retrieve statistics", 500)

@phase4_export_bp.route('/cleanup', methods=['POST'])
def cleanup_old_jobs():
    """Clean up old completed export jobs."""
    try:
        data = request.get_json() if request.is_json else {}
        max_age_hours = data.get('max_age_hours', 24)
        
        jobs_before = len(social_exporter.active_jobs)
        social_exporter.clean_completed_jobs(max_age_hours)
        jobs_after = len(social_exporter.active_jobs)
        
        cleaned_jobs = jobs_before - jobs_after
        
        return success_response({
            'jobs_cleaned': cleaned_jobs,
            'jobs_remaining': jobs_after,
            'max_age_hours': max_age_hours
        })
        
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        return error_response("Cleanup failed", 500)

# =============================================================================
# Blueprint Registration Function
# =============================================================================

def register_phase4_export_blueprint(app):
    """Register the Phase 4 export blueprint with the Flask app."""
    app.register_blueprint(phase4_export_bp)
    logger.info("Phase 4 export endpoints registered successfully")