"""Subtitle-related API endpoints extracted from legacy app.py.

Endpoints preserved:
  POST /api/subtitles/generate
  POST /api/subtitles/export  (legacy JSON burn-in pipeline)
  GET  /api/subtitles/presets
  POST /api/subtitles/generate-enhanced
  POST /api/subtitles/validate
  POST /api/subtitles/optimize
  POST /api/video/upload (kept here due to tight coupling with subtitle workflows)

All endpoints keep their original paths for backward compatibility.
"""
from __future__ import annotations

import os, time, json
from flask import Blueprint, request, jsonify
from api_responses import success_response, error_response
from logger import app_logger as logger
from error_utils import log_exception
from werkzeug.utils import secure_filename

subtitles_bp = Blueprint('subtitles', __name__)


def _try_import(name: str, symbol: str):  # small helper
    try:  # pragma: no cover - import side effect
        module = __import__(name, fromlist=[symbol])
        return getattr(module, symbol)
    except Exception:
        return None


@subtitles_bp.route('/api/subtitles/generate', methods=['POST'])
def generate_subtitles():
    try:
        data = request.get_json() or {}
        audio_filename = data.get('audio_filename')
        text = (data.get('text') or '').strip()
        platform_preset = data.get('platform_preset', 'youtube-landscape')
        if not audio_filename or not text:
            return error_response("Missing required fields: audio_filename, text", 400)
        audio_path = os.path.join(subtitles_bp.root_path, '..', 'uploads', audio_filename)
        if not os.path.exists(audio_path):
            return error_response(f"Audio file not found: {audio_filename}", 404)
        SubtitleEngine = _try_import('subtitle_engine', 'SubtitleEngine')
        SubtitleStyle = _try_import('subtitle_engine', 'SubtitleStyle')
        SubtitleRenderer = _try_import('subtitle_renderer', 'SubtitleRenderer')
        if not SubtitleEngine:
            logger.error("Subtitle modules not available")
            return error_response("Subtitle generation not available", 503)
        # Alignment dependency
        audio_aligner_instance = _try_import('audio_aligner', 'audio_aligner_instance')
        ENHANCED_ALIGNMENT_AVAILABLE = bool(_try_import('enhanced_alignment_demo', 'ENHANCED_ALIGNMENT_AVAILABLE')) or hasattr(audio_aligner_instance, 'align_audio_to_text_enhanced')
        alignment_result = None; timeline = []; frame_states = []
        try:
            if ENHANCED_ALIGNMENT_AVAILABLE and hasattr(audio_aligner_instance, 'align_audio_to_text_enhanced'):
                alignment_result, timeline, frame_states = audio_aligner_instance.align_audio_to_text_enhanced(
                    audio_path=audio_path,
                    transcript=text,
                    language=data.get('language', 'pt-BR'),
                    fps=data.get('fps', 30.0),
                    method=data.get('method', 'auto')
                )
            else:
                alignment_result = audio_aligner_instance.align_audio_to_text(
                    audio_path=audio_path,
                    transcript=text,
                    language=data.get('language', 'pt-BR')
                )
        except Exception as e:  # noqa: BLE001
            logger.error("Audio alignment failed: %s", e)
            return error_response(f"Audio alignment failed: {e}", 500)
        try:
            subtitle_engine = SubtitleEngine(audio_aligner_instance)
            subtitles = subtitle_engine.generate_subtitles_from_alignment(
                alignment_result,
                max_chars_per_line=data.get('max_chars_per_line', 40),
                max_duration_ms=data.get('max_duration_ms', 3000)
            )
            if platform_preset and platform_preset != 'custom':
                subtitles, style = subtitle_engine.optimize_for_platform(subtitles, platform_preset)
            else:
                style = SubtitleStyle()
            validation = subtitle_engine.validate_subtitles(subtitles)
            subtitles_data = [{
                'id': sub.id,
                'text': sub.text,
                'start_ms': sub.start_ms,
                'end_ms': sub.end_ms,
                'confidence': sub.confidence,
                'duration_ms': sub.end_ms - sub.start_ms
            } for sub in subtitles]
            style_data = {
                'font_family': style.font_family,
                'font_size': style.font_size,
                'font_weight': style.font_weight,
                'text_color': style.text_color,
                'background_color': style.background_color,
                'background_opacity': style.background_opacity,
                'outline_color': style.outline_color,
                'outline_width': style.outline_width,
                'vertical_position': style.vertical_position,
                'horizontal_align': style.horizontal_align,
                'max_width': style.max_width
            }
            return success_response({
                'subtitles': subtitles_data,
                'style': style_data,
                'validation': validation,
                'platform_preset': platform_preset,
                'alignment_info': {
                    'language': getattr(alignment_result, 'language', ''),
                    'total_tokens': len(getattr(alignment_result, 'tokens', [])),
                    'avg_confidence': getattr(getattr(alignment_result, 'stats', None), 'avg_confidence', 0.0)
                }
            })
        except Exception as e:  # noqa: BLE001
            logger.error("Subtitle generation failed: %s", e)
            return error_response(f"Subtitle generation failed: {e}", 500)
    except Exception as e:  # noqa: BLE001
        logger.error("Unexpected error in subtitle generation: %s", e)
        log_exception(logger, e)
        return error_response("Internal server error", 500)


@subtitles_bp.route('/api/subtitles/export', methods=['POST'], endpoint='subtitles_export')
def export_subtitles_export():
    try:
        data = request.get_json() or {}
        video_filename = data.get('video_filename')
        subtitles_data = data.get('subtitles', [])
        style_data = data.get('style', {})
        platform_preset = data.get('platform_preset', 'youtube-landscape')
        if not video_filename or not subtitles_data:
            return error_response("Missing required fields: video_filename, subtitles", 400)
        SubtitleSegment = _try_import('subtitle_engine', 'SubtitleSegment')
        SubtitleStyle = _try_import('subtitle_engine', 'SubtitleStyle')
        SubtitleRenderer = _try_import('subtitle_renderer', 'SubtitleRenderer')
        if not (SubtitleSegment and SubtitleStyle and SubtitleRenderer):
            logger.error("Subtitle modules not available for export")
            return error_response("Subtitle rendering not available", 503)
        uploads_root = os.path.join(subtitles_bp.root_path, '..', 'uploads')
        video_path = os.path.join(uploads_root, video_filename)
        if not os.path.exists(video_path):
            return error_response(f"Video file not found: {video_filename}", 404)
        subtitles = [
            SubtitleSegment(
                id=sub_data.get('id', 0),
                text=sub_data.get('text', ''),
                start_ms=sub_data.get('start_ms', 0),
                end_ms=sub_data.get('end_ms', 1000),
                confidence=sub_data.get('confidence', 1.0)
            ) for sub_data in subtitles_data
        ]
        style = SubtitleStyle(
            font_family=style_data.get('font_family', 'Arial, sans-serif'),
            font_size=style_data.get('font_size', 24),
            font_weight=style_data.get('font_weight', 'bold'),
            text_color=style_data.get('text_color', '#ffffff'),
            background_color=style_data.get('background_color', '#000000'),
            background_opacity=style_data.get('background_opacity', 0.7),
            outline_color=style_data.get('outline_color', '#000000'),
            outline_width=style_data.get('outline_width', 2),
            vertical_position=style_data.get('vertical_position', 'bottom'),
            horizontal_align=style_data.get('horizontal_align', 'center'),
            max_width=style_data.get('max_width', 80)
        )
        base_name = os.path.splitext(os.path.basename(video_filename))[0]
        output_filename = f"{base_name}_with_subtitles.mp4"
        output_path = os.path.join(uploads_root, output_filename)
        renderer = SubtitleRenderer()
        preset = None
        if platform_preset != 'custom':
            preset = renderer.platform_presets.get(platform_preset)
        def progress_callback(percent, message):  # pragma: no cover
            logger.info("Export progress: %s", message)
        result_path = renderer.render_subtitles_on_video(
            input_video_path=video_path,
            subtitles=subtitles,
            style=style,
            output_video_path=output_path,
            preset=preset,
            progress_callback=progress_callback
        )
        if os.path.exists(result_path):
            size_mb = os.path.getsize(result_path)/(1024*1024)
            return success_response({
                'output_filename': output_filename,
                'file_size_mb': round(size_mb, 2),
                'download_url': f'/api/export/download/{output_filename}',
                'subtitles_count': len(subtitles),
                'platform_preset': platform_preset
            })
        return error_response("Video export failed - output file not created", 500)
    except Exception as e:  # noqa: BLE001
        logger.error("Unexpected error in video export: %s", e)
        log_exception(logger, e)
        return error_response("Internal server error", 500)


@subtitles_bp.route('/api/subtitles/presets', methods=['GET'])
def get_subtitle_presets():
    try:
        SubtitleEngine = _try_import('subtitle_engine', 'SubtitleEngine')
        if not SubtitleEngine:
            return error_response("Subtitle presets not available", 503)
        engine = SubtitleEngine()
        presets_data = {}
        for preset_name, preset in engine.platform_presets.items():
            presets_data[preset_name] = {
                'name': preset.name,
                'aspect_ratio': preset.aspect_ratio,
                'resolution': preset.resolution,
                'max_duration': preset.max_duration,
                'style': {
                    'font_size': preset.style.font_size,
                    'font_weight': preset.style.font_weight,
                    'text_color': preset.style.text_color,
                    'background_color': preset.style.background_color,
                    'background_opacity': preset.style.background_opacity,
                    'outline_width': preset.style.outline_width,
                    'vertical_position': preset.style.vertical_position,
                    'horizontal_align': preset.style.horizontal_align,
                    'max_width': preset.style.max_width
                }
            }
        return success_response({'presets': presets_data, 'default_preset': 'youtube-landscape'})
    except Exception as e:  # noqa: BLE001
        logger.error("Error getting subtitle presets: %s", e)
        return error_response("Internal server error", 500)


@subtitles_bp.route('/api/subtitles/generate-enhanced', methods=['POST'])
def generate_enhanced_subtitles():
    try:
        data = request.get_json() or {}
        alignment_result = data.get('alignment')
        platform = data.get('platform', 'custom')
        custom_options = data.get('custom_options', {})
        if not alignment_result:
            return error_response("No alignment data provided", 400)
        EnhancedSubtitleEngine = _try_import('enhanced_subtitle_engine', 'EnhancedSubtitleEngine')
        if EnhancedSubtitleEngine:
            engine = EnhancedSubtitleEngine()
            segments = engine.generate_intelligent_subtitles(alignment_result, platform, custom_options)
            metrics = engine.get_performance_metrics()
            return success_response({
                'segments': [{
                    'id': seg.id,
                    'text': seg.text,
                    'start_time': seg.start_time,
                    'end_time': seg.end_time,
                    'confidence': seg.confidence,
                    'word_count': seg.word_count,
                    'reading_speed': seg.reading_speed,
                    'platform_optimized': seg.platform_optimized,
                    'style_overrides': seg.style_overrides
                } for seg in segments],
                'metrics': metrics,
                'count': len(segments),
                'enhanced': True
            })
        SubtitleEngine = _try_import('subtitle_engine', 'SubtitleEngine')
        if not SubtitleEngine:
            return error_response("Subtitle engine not available", 503)
        engine = SubtitleEngine()
        subs = engine.generate_subtitles_from_alignment(alignment_result, {})
        return success_response({'segments': subs, 'count': len(subs), 'enhanced': False, 'fallback': True})
    except Exception as e:  # noqa: BLE001
        logger.error("Enhanced subtitle generation failed: %s", e)
        log_exception(logger, e)
        return error_response("Enhanced subtitle generation failed", 500)


@subtitles_bp.route('/api/subtitles/validate', methods=['POST'])
def validate_subtitles():
    try:
        data = request.get_json() or {}
        segments_data = data.get('segments', [])
        platform = data.get('platform', 'custom')
        if not segments_data:
            return error_response("No subtitle segments provided", 400)
        platform_constraints = {
            'instagram_story': {'max_chars_per_line': 35, 'max_lines': 2, 'max_duration': 15},
            'instagram_reel': {'max_chars_per_line': 40, 'max_lines': 2, 'max_duration': 90},
            'tiktok': {'max_chars_per_line': 38, 'max_lines': 2, 'max_duration': 60},
            'youtube_shorts': {'max_chars_per_line': 42, 'max_lines': 2, 'max_duration': 60},
            'custom': {'max_chars_per_line': 50, 'max_lines': 3, 'max_duration': 300}
        }
        constraints = platform_constraints.get(platform, platform_constraints['custom'])
        validation_results = []
        issues = []
        for i, seg in enumerate(segments_data):
            seg_issues = []
            start = float(seg.get('start_time', 0)); end = float(seg.get('end_time', 0)); dur = end - start
            if dur <= 0: seg_issues.append('Invalid duration: end time must be after start time')
            if dur < 0.3: seg_issues.append('Duration too short: minimum 0.3 seconds recommended')
            text = seg.get('text', '')
            lines = text.split('\n')
            if len(lines) > constraints['max_lines']:
                seg_issues.append(f'Too many lines: {len(lines)} > {constraints["max_lines"]}')
            for line in lines:
                if len(line) > constraints['max_chars_per_line']:
                    seg_issues.append(f'Line too long: {len(line)} > {constraints["max_chars_per_line"]} chars')
            words = text.replace('\n', ' ').split()
            wc = len(words)
            rs = wc / dur if dur > 0 else 0
            if rs > 4.0: seg_issues.append(f'Reading speed too fast: {rs:.1f} > 4.0 words/sec')
            elif rs < 1.5 and wc > 0: seg_issues.append(f'Reading speed too slow: {rs:.1f} < 1.5 words/sec')
            if i < len(segments_data) - 1:
                next_start = float(segments_data[i+1].get('start_time', 0))
                if end > next_start: seg_issues.append('Overlaps with next segment')
            validation_results.append({'segment_id': seg.get('id', f'seg_{i}'), 'is_valid': not seg_issues, 'issues': seg_issues, 'reading_speed': round(rs,2), 'duration': round(dur,2), 'word_count': wc})
            issues.extend(seg_issues)
        overall_valid = not issues
        return success_response({'is_valid': overall_valid, 'total_issues': len(issues), 'segment_results': validation_results, 'platform_constraints': constraints})
    except Exception as e:  # noqa: BLE001
        logger.error("Subtitle validation failed: %s", e)
        log_exception(logger, e)
        return error_response("Subtitle validation failed", 500)


@subtitles_bp.route('/api/subtitles/optimize', methods=['POST'])
def optimize_subtitles_for_platform():
    try:
        data = request.get_json() or {}
        segments_data = data.get('segments', [])
        target_platform = data.get('platform', 'custom')
        if not segments_data:
            return error_response("No subtitle segments provided", 400)
        platform_settings = {
            'instagram_story': {'max_chars_per_line':35,'max_lines':2,'font_size':48,'position':'bottom','style':{'font_weight':'bold','color':'#FFFFFF','background_opacity':0.7}},
            'instagram_reel': {'max_chars_per_line':40,'max_lines':2,'font_size':44,'position':'bottom','style':{'font_weight':'bold','color':'#FFFFFF','background_opacity':0.6}},
            'tiktok': {'max_chars_per_line':38,'max_lines':2,'font_size':46,'position':'bottom','style':{'font_weight':'bold','color':'#FFFFFF','background_opacity':0.8}},
            'youtube_shorts': {'max_chars_per_line':42,'max_lines':2,'font_size':42,'position':'bottom','style':{'font_weight':'bold','color':'#FFFFFF','background_opacity':0.75}},
            'custom': {'max_chars_per_line':50,'max_lines':3,'font_size':36,'position':'bottom','style':{'font_weight':'normal','color':'#FFFFFF','background_opacity':0.8}},
        }
        settings = platform_settings.get(target_platform, platform_settings['custom'])
        optimized_segments = []
        for seg in segments_data:
            text = seg.get('text','')
            optimized_text = _optimize_text_for_platform(text, settings)
            optimized_segments.append({
                'id': seg.get('id'),
                'text': optimized_text,
                'start_time': seg.get('start_time'),
                'end_time': seg.get('end_time'),
                'confidence': seg.get('confidence',1.0),
                'platform_optimized': {target_platform: {'font_size': settings['font_size'], 'position': settings['position'], 'style_preset': settings['style']}}
            })
        return success_response({'optimized_segments': optimized_segments,'platform': target_platform,'settings_applied': settings})
    except Exception as e:  # noqa: BLE001
        logger.error("Subtitle optimization failed: %s", e)
        log_exception(logger, e)
        return error_response("Subtitle optimization failed", 500)


def _optimize_text_for_platform(text: str, settings: dict):
    max_chars = settings['max_chars_per_line']; max_lines = settings['max_lines']
    words = text.replace('\n',' ').split(); lines=[]; curr=[]; length=0
    for w in words:
        wl = len(w) + (1 if curr else 0)
        if length + wl <= max_chars:
            curr.append(w); length += wl
        else:
            if curr: lines.append(' '.join(curr))
            if len(lines) >= max_lines: break
            curr=[w]; length=len(w)
    if curr and len(lines) < max_lines: lines.append(' '.join(curr))
    return '\n'.join(lines)


@subtitles_bp.route('/api/video/upload', methods=['POST'])
def upload_video():
    try:
        if 'video' not in request.files:
            return error_response("No video file provided", 400)
        file = request.files['video']
        if file.filename == '':
            return error_response("No file selected", 400)
        allowed_ext = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.m4v'}
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in allowed_ext:
            return error_response(f"Unsupported video format: {ext}", 400)
        ts = int(time.time())
        unique_name = f"video_{ts}_{secure_filename(file.filename)}"
        upload_folder = os.path.join(subtitles_bp.root_path, '..', 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        target_path = os.path.join(upload_folder, unique_name)
        file.save(target_path)
        size = os.path.getsize(target_path)
        return success_response({'filename': unique_name,'original_filename': file.filename,'file_size_bytes': size,'file_size_mb': round(size/(1024*1024),2),'file_extension': ext})
    except Exception as e:  # noqa: BLE001
        logger.error("Video upload failed: %s", e)
        log_exception(logger, e)
        return error_response("Video upload failed", 500)


__all__ = ['subtitles_bp']
