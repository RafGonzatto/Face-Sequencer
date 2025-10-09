"""Subtitles basic endpoints.

Endpoints:
  POST /api/subtitles/generate { filename, text, language? }
  GET  /api/subtitles/presets
  POST /api/subtitles/validate { subtitles: [...] }
"""
from __future__ import annotations
from flask import Blueprint, request, jsonify, make_response

from app.core.subtitles.subtitle_engine import SubtitleEngine, SubtitleStyle
from app.core.audio.audio_aligner import AudioAligner
from app.core.utils.api_responses import success_response, error_response
import os

subtitles_bp = Blueprint("subtitles_basic", __name__)

_subtitle_engine: SubtitleEngine | None = None
_aligner: AudioAligner | None = None


def _get_engine() -> SubtitleEngine:
    global _subtitle_engine, _aligner
    if _aligner is None:
        _aligner = AudioAligner()
    if _subtitle_engine is None:
        _subtitle_engine = SubtitleEngine(audio_aligner=_aligner)
    return _subtitle_engine


@subtitles_bp.route("/api/subtitles/presets", methods=["GET"])
def list_presets():
    try:
        engine = _get_engine()
        out = {}
        for k, preset in engine.platform_presets.items():
            out[k] = {
                'name': preset.name,
                'aspect_ratio': preset.aspect_ratio,
                'resolution': preset.resolution,
                'max_duration': preset.max_duration,
                'style': {k2: getattr(preset.style, k2) for k2 in vars(preset.style) if not k2.startswith('_')}
            }
        return jsonify(success_response('Subtitle presets', presets=out))
    except Exception as e:  # noqa: BLE001
        # Provide minimal fallback so UI can proceed
        from app.core.utils.api_responses import error_response as _er
        try:
            import traceback, sys
            traceback.print_exc(file=sys.stderr)
        except Exception:  # noqa: BLE001
            pass
        fallback = {
            'basic': {
                'name': 'Basic',
                'aspect_ratio': '16:9',
                'resolution': '1920x1080',
                'max_duration': 600,
                'style': {
                    'fontFamily': 'Arial',
                    'fontSize': 32,
                    'color': '#FFFFFF',
                    'bgColor': 'rgba(0,0,0,0.6)',
                    'bgOpacity': 1,
                    'padding': 8,
                    'borderRadius': 4,
                    'textAlign': 'center',
                    'marginY': 40,
                    'maxWidth': 80,
                }
            }
        }
        return jsonify(_er(f"Failed to load presets: {e}", error_type='presets_error', status=500, presets=fallback)), 500


@subtitles_bp.route("/api/subtitles/generate", methods=["POST"])
def generate_subtitles():
    """Generate subtitles from audio + transcript.

    Adds better diagnostics & optional naive fallback segmentation by passing
    { fallback: true } in body (or using ?fallback=1).
    """
    data = request.get_json() or {}
    filename = data.get('filename') or data.get('audio_filename')
    text = (data.get('text') or '').strip()
    language = data.get('language') or 'pt-BR'
    platform = data.get('platform_preset') or 'youtube-landscape'
    # Options from UI
    char_level = bool(data.get('character_level'))  # character/"syllable" style
    force_uppercase = bool(data.get('uppercase'))
    fallback_flag = (
        str(data.get('fallback', '')).lower() in {"1", "true", "yes"}
        or request.args.get('fallback') in {"1", "true"}
    )
    if not filename or not text:
        return jsonify(error_response('Missing filename or text', error_type='validation_error', status=400)), 400
    from flask import current_app
    audio_folder = current_app.config.get('AUDIO_FOLDER') or os.path.join(current_app.root_path, '..', 'uploads', 'audio')
    audio_path = os.path.join(audio_folder, filename)
    if not os.path.exists(audio_path):
        return jsonify(error_response('Audio file not found', error_type='not_found', status=404)), 404

    def _naive_segment(total_ms: int, raw_text: str):
        """Fallback segmentation: split by punctuation / sentence, distribute time evenly."""
        import re, math
        sentences = [s.strip() for s in re.split(r'[\.!?\n]+', raw_text) if s.strip()]
        if not sentences:
            sentences = [raw_text]
        slice_ms = total_ms / len(sentences)
        subs = []
        t = 0.0
        for idx, sent in enumerate(sentences):
            start = int(t)
            end = int(min(total_ms, t + slice_ms))
            if end <= start:
                end = start + 500
            subs.append({
                'id': idx + 1,
                'text': sent,
                'start_ms': start,
                'end_ms': end,
                'duration_ms': end - start,
                'confidence': 0.0,
            })
            t += slice_ms
        return subs

    try:
        engine = _get_engine()
        if fallback_flag:
            # Only compute audio duration quickly
            try:
                import librosa
                import soundfile as sf  # type: ignore
                dur = None
                try:
                    info = sf.info(audio_path)
                    dur = info.frames / float(info.samplerate)
                except Exception:
                    y, sr = librosa.load(audio_path, sr=None, mono=True)
                    dur = len(y) / sr
                total_ms = int(dur * 1000)
            except Exception:
                total_ms = 60_000  # default 1min
            subs = _naive_segment(total_ms, text)
            style = engine.platform_presets.get(platform, engine.platform_presets['youtube-landscape']).style
            style_data = {k: getattr(style, k) for k in vars(style) if not k.startswith('_')}
            return jsonify(success_response('Subtitles generated (fallback)', subtitles=subs, style=style_data, platform_preset=platform, fallback=True))

        # Full alignment path
        alignment = engine.audio_aligner.align_audio_to_text(
            audio_path,
            text,
            language=language,
            char_level=char_level,
        )
        segments = engine.generate_subtitles_from_alignment(alignment)

        # --- Post-processing to improve readability and Portuguese-specific fixes ---
        # 1) Normalize spaces around punctuation inside each segment
        # 2) Attach punctuation-only segments (e.g., "!", ".") to the previous segment
        # 3) Apply common PT-BR contractions across segment boundaries (de+o=do, em+o=no, por+o=pelo, a+o=ao, etc.)
        import re

        def _normalize_punctuation_spacing(t: str) -> str:
            if not t:
                return t
            # Remove spaces before punctuation
            t = re.sub(r"\s+([,.;:!?])", r"\1", t)
            # Ensure a single space after punctuation when followed by a letter/number
            t = re.sub(r"([,.;:!?])(\w)", r"\1 \2", t)
            # Collapse multiple spaces
            t = re.sub(r"\s{2,}", " ", t)
            return t.strip()

        def _is_punct_only(t: str) -> bool:
            t = (t or "").strip()
            return bool(t) and re.fullmatch(r"[!?,.;:…]+", t) is not None

        # Normalize punctuation spacing inside each segment
        for _s in segments:
            try:
                _s.text = _normalize_punctuation_spacing(getattr(_s, 'text', ''))
            except Exception:
                pass

        # Attach punctuation-only segments to previous and extend previous end time
        # BUT only when the punctuation segment is extremely short; otherwise keep it separate
        merged: list = []
        for _s in segments:
            txt = getattr(_s, 'text', '')
            if merged and _is_punct_only(txt):
                duration = 0
                try:
                    duration = max(0, int(getattr(_s, 'end_ms', 0)) - int(getattr(_s, 'start_ms', 0)))
                except Exception:
                    duration = 0
                if duration <= 150:  # merge only if tiny punctuation blip
                    prev = merged[-1]
                    prev.text = (_normalize_punctuation_spacing(f"{getattr(prev, 'text', '')}{txt}"))
                    try:
                        # extend timing to include the punctuation segment duration
                        if hasattr(prev, 'end_ms') and hasattr(_s, 'end_ms'):
                            prev.end_ms = max(getattr(prev, 'end_ms'), getattr(_s, 'end_ms'))
                    except Exception:
                        pass
                    # drop current punctuation-only segment
                    continue
            merged.append(_s)

        segments = merged

        # Portuguese contractions across segment boundaries
        CONTRACTIONS = {
            ('de', 'o'): 'do', ('de', 'a'): 'da', ('de', 'os'): 'dos', ('de', 'as'): 'das',
            ('em', 'o'): 'no', ('em', 'a'): 'na', ('em', 'os'): 'nos', ('em', 'as'): 'nas',
            ('por', 'o'): 'pelo', ('por', 'a'): 'pela', ('por', 'os'): 'pelos', ('por', 'as'): 'pelas',
            ('a', 'o'): 'ao', ('a', 'os'): 'aos', ('a', 'a'): 'à', ('a', 'as'): 'às',
        }

        def _apply_contraction(prev_text: str, next_text: str) -> tuple[str, str]:
            if not prev_text or not next_text:
                return prev_text, next_text
            prev_text_stripped = prev_text.rstrip()
            next_text_stripped = next_text.lstrip()
            # Capture last word of prev and first word of next (case-insensitive)
            prev_match = re.search(r"(?i)\b(\w+)\s*$", prev_text_stripped)
            next_match = re.match(r"(?i)^(\w+)(\b\s+|\b)", next_text_stripped)
            if not prev_match or not next_match:
                return prev_text, next_text
            prev_last = prev_match.group(1).lower()
            next_first = next_match.group(1).lower()
            repl = CONTRACTIONS.get((prev_last, next_first))
            if not repl:
                return prev_text, next_text
            # Replace prev last word with contraction and remove article from next
            new_prev = re.sub(rf"(?i)\b{re.escape(prev_last)}\s*$", repl, prev_text_stripped)
            # Remove the first word (article) from next
            new_next = re.sub(rf"(?i)^\s*{re.escape(next_first)}(\b\s+|\b)", "", next_text_stripped, count=1)
            # Cleanup spaces around punctuation
            return _normalize_punctuation_spacing(new_prev), _normalize_punctuation_spacing(new_next)

        for i in range(len(segments) - 1):
            try:
                p = segments[i]
                n = segments[i + 1]
                new_prev, new_next = _apply_contraction(getattr(p, 'text', ''), getattr(n, 'text', ''))
                p.text = new_prev
                n.text = new_next
            except Exception:
                continue

        # If original transcript used '/', prefer rendering as '/' instead of spoken 'barra'
        try:
            if '/' in text:
                pattern = re.compile(r'(?i)(?<=\w)\s+barra\s+(?=\w)')
                for _s in segments:
                    _s.text = pattern.sub(' / ', getattr(_s, 'text', ''))
        except Exception:
            pass
        style = engine.platform_presets.get(platform, engine.platform_presets['youtube-landscape']).style
        payload_segments = [
            {
                'id': s.id,
                'text': (s.text.upper() if force_uppercase else s.text),
                'start_ms': s.start_ms,
                'end_ms': s.end_ms,
                'duration_ms': s.end_ms - s.start_ms,
                'confidence': s.confidence,
            } for s in segments
        ]
        style_data = {k: getattr(style, k) for k in vars(style) if not k.startswith('_')}
        return jsonify(success_response('Subtitles generated', subtitles=payload_segments, style=style_data, platform_preset=platform, fallback=False))
    except Exception as e:  # noqa: BLE001
        # Log verbose stack for diagnostics
        import traceback, sys
        traceback.print_exc(file=sys.stderr)
        # Offer naive fallback automatically if alignment failed & not already fallback
        if not fallback_flag:
            try:
                # Try to get duration without relying on full engine stack
                total_ms = 60_000
                try:
                    import soundfile as sf  # type: ignore
                    info = sf.info(audio_path)
                    total_ms = int(info.frames / float(info.samplerate) * 1000)
                except Exception:
                    try:
                        import librosa
                        y_tmp, sr_tmp = librosa.load(audio_path, sr=None, mono=True)
                        total_ms = int(len(y_tmp) / sr_tmp * 1000)
                    except Exception:
                        pass
                subs = _naive_segment(total_ms, text)
                # Style fallback (static) if engine itself is broken
                style_data = {
                    'fontFamily': 'Arial, sans-serif',
                    'fontSize': 28,
                    'color': '#FFFFFF',
                    'bgColor': 'rgba(0,0,0,0.6)',
                    'bgOpacity': 1,
                    'padding': 8,
                    'borderRadius': 4,
                    'textAlign': 'center',
                    'marginY': 40,
                    'maxWidth': 80,
                }
                try:
                    engine2 = _get_engine()
                    style2 = engine2.platform_presets.get(platform, engine2.platform_presets['youtube-landscape']).style
                    style_data = {k: getattr(style2, k) for k in vars(style2) if not k.startswith('_')}
                except Exception:
                    pass
                return jsonify(success_response('Subtitles generated (auto-fallback)', subtitles=subs, style=style_data, platform_preset=platform, fallback=True, error=str(e))), 206
            except Exception:
                # If even fallback failed, proceed to 500
                pass
        return jsonify(error_response(str(e), error_type='subtitle_error', status=500)), 500


def _format_timestamp_srt(seconds: float) -> str:
    ms_total = int(round(seconds * 1000))
    h, rem = divmod(ms_total, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

def _format_timestamp_vtt(seconds: float) -> str:
    ms_total = int(round(seconds * 1000))
    h, rem = divmod(ms_total, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02}:{m:02}:{s:02}.{ms:03}"

@subtitles_bp.route('/api/subtitles/export', methods=['POST'])
def export_subtitles():
    data = request.get_json() or {}
    subs = data.get('subtitles') or []
    fmt = (data.get('format') or 'srt').lower()
    # Optional line wrapping controls
    wrap_lines = bool(data.get('wrap_lines'))
    try:
        wrap_min = int(data.get('wrap_min', 20))
        wrap_max = int(data.get('wrap_max', 26))
    except Exception:
        wrap_min, wrap_max = 20, 26
    wrap_min = max(10, min(wrap_min, 200))
    wrap_max = max(wrap_min, min(wrap_max, 240))
    if fmt not in {"srt", "vtt"}:
        return jsonify(error_response('Unsupported format', error_type='validation_error', status=400)), 400
    if not isinstance(subs, list) or not subs:
        return jsonify(error_response('No subtitles provided', error_type='validation_error', status=400)), 400
    # Normalize entries: allow start/end (sec) or start_ms/end_ms
    # Normalize into a clean list of (start_sec, end_sec, text) without holes
    normalized: list[tuple[float, float, str]] = []
    for _, s in enumerate(subs, start=1):
        start_sec = None
        end_sec = None
        if 'start_ms' in s and 'end_ms' in s:
            start_sec = float(s['start_ms']) / 1000.0
            end_sec = float(s['end_ms']) / 1000.0
        else:
            start_sec = float(s.get('start', 0))
            end_sec = float(s.get('end', start_sec))
        text = (s.get('text') or '').strip()
        if not text:
            continue
        if end_sec <= start_sec:
            end_sec = start_sec + 0.5
        normalized.append((start_sec, end_sec, text))
    if not normalized:
        return jsonify(error_response('No valid subtitles after normalization', error_type='validation_error', status=400)), 400
    # Helper: soft wrap text between wrap_min and wrap_max, avoiding word splits
    def _soft_wrap(text: str) -> list[str]:
        import re
        t = (text or '').strip()
        if not wrap_lines:
            return [t]
        words = re.split(r"(\s+)", t)
        out: list[str] = []
        line = ''
        def push_line():
            nonlocal line
            if line.strip():
                out.append(line.rstrip())
            line = ''
        for token in words:
            tentative = (line + token)
            length = len(tentative.strip())
            if not line:
                line = token.lstrip()
                continue
            if length <= wrap_max:
                line = tentative
            else:
                # If current line reached at least wrap_min, break before token
                if len(line.strip()) >= wrap_min:
                    push_line()
                    line = token.lstrip()
                else:
                    # Force break at closest space within limits
                    push_line()
                    line = token.lstrip()
        push_line()
        # Post-trim lines
        return [L.strip() for L in out if L.strip()]

    lines: list[str] = []
    if fmt == 'srt':
        for i, (start, end, text) in enumerate(normalized, start=1):
            lines.append(str(i))
            lines.append(f"{_format_timestamp_srt(start)} --> {_format_timestamp_srt(end)}")
            # Replace hard newlines then optionally wrap
            wrapped = _soft_wrap(text.replace('\r', ' ').replace('\n', ' '))
            if wrapped:
                lines.extend(wrapped)
            else:
                lines.append('')
            lines.append("")
        # Use CRLF line endings for maximum compatibility with Windows editors (e.g., Kdenlive)
        content = "\r\n".join(lines)
        mimetype = 'application/x-subrip'
        filename = 'subtitles.srt'
    else:  # vtt
        lines.append('WEBVTT')
        lines.append('')
        for start, end, text in normalized:
            lines.append(f"{_format_timestamp_vtt(start)} --> {_format_timestamp_vtt(end)}")
            wrapped = _soft_wrap(text.replace('\r', ' ').replace('\n', ' '))
            lines.extend(wrapped if wrapped else [''])
            lines.append("")
        content = "\n".join(lines)
        mimetype = 'text/vtt'
        filename = 'subtitles.vtt'
    resp = make_response(content)
    resp.headers['Content-Type'] = mimetype + '; charset=utf-8'
    resp.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
    return resp


@subtitles_bp.route("/api/subtitles/validate", methods=["POST"])
def validate_subtitles():
    data = request.get_json() or {}
    subs = data.get('subtitles') or []
    if not isinstance(subs, list):
        return jsonify(error_response('Invalid subtitles array', error_type='validation_error', status=400)), 400
    issues = []
    last_end = 0
    for idx, s in enumerate(subs):
        start = s.get('start_ms', 0)
        end = s.get('end_ms', start)
        text = (s.get('text') or '').strip()
        if end <= start:
            issues.append({'index': idx, 'type': 'timing', 'message': 'end_ms <= start_ms'})
        if start < last_end:
            issues.append({'index': idx, 'type': 'overlap', 'message': 'Overlap with previous'})
        if not text:
            issues.append({'index': idx, 'type': 'empty', 'message': 'Empty text'})
        last_end = max(last_end, end)
    return jsonify(success_response('Validation complete', valid=len(issues)==0, issues=issues))

__all__ = ["subtitles_bp"]