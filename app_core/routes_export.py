"""Unified export-related endpoints extracted from app.py legacy sections.

Contains:
  - /api/export/validate/<task_id>
  - /api/export/download/<task_id>
  - /api/export/video-with-subtitles (burn-in subtitles)
  - /api/export/video/burned/<filename>

Note: There is an existing `export_bp` (JSON/MP4 sequence export + SSE) in
`export_endpoints.py` and a phase4 export blueprint under `/api/v4/export`.
This module only relocates the residual legacy routes still defined directly
on the app object to reduce app.py size. It keeps the same URL paths.
"""
from __future__ import annotations

import os, json, uuid, time, hashlib, re, subprocess, threading
from pathlib import Path
from flask import Blueprint, jsonify, send_file, request
from werkzeug.utils import secure_filename
from api_responses import success_response, error_response

export_legacy_bp = Blueprint("export_legacy", __name__)


def _validate_mp4_file(file_path: str):
    if not os.path.exists(file_path):
        return False, "File not found", 0
    file_size = os.path.getsize(file_path)
    if file_size < 1024:
        return False, f"File too small ({file_size} bytes)", file_size
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()
            if first_line.lower().startswith("error"):
                return False, f"File contains error message: {first_line}", file_size
    except UnicodeDecodeError:
        pass
    try:
        with open(file_path, 'rb') as f:
            header = f.read(16)
            if not any(sig in header for sig in (b'ftyp', b'mdat', b'moov', b'free')):
                return False, "Invalid MP4 signature", file_size
    except Exception as e:  # noqa: BLE001
        return False, f"Error reading file header: {e}", file_size
    try:  # optional ffprobe
        subprocess.run(['ffprobe', '-v', 'error', file_path], capture_output=True, text=True, timeout=3)
    except Exception:
        pass
    return True, f"Valid MP4 file ({file_size} bytes)", file_size


@export_legacy_bp.route('/api/export/validate/<task_id>', methods=['GET'])
def validate_export(task_id):  # pragma: no cover - thin wrapper
    from flask import current_app
    app_state = current_app.config['app_state']
    try:
        if task_id not in app_state['export_tasks']:
            return jsonify(error_response('Task not found', error_type='not_found', status=404)), 404
        task = app_state['export_tasks'][task_id]
        if task['status'] != 'completed':
            return jsonify(error_response('Export not completed', error_type='invalid_state', status=400, details={'status': task['status'], 'progress': task['progress'], 'message': task['message']})), 400
        is_valid, msg, size = _validate_mp4_file(task['path'])
        if not is_valid:
            task['status'] = 'error'
            task['error'] = msg
            return jsonify(error_response(msg, error_type='validation_failed', status=400, details={'valid': False, 'fileSize': size, 'filename': task['filename']})), 400
        return jsonify(success_response(msg, valid=True, fileSize=size, filename=task['filename']))
    except Exception as e:  # noqa: BLE001
        return jsonify(error_response(str(e), error_type='unexpected_error', status=400)), 400


@export_legacy_bp.route('/api/export/download/<task_id>', methods=['GET'])
def download_export(task_id):  # pragma: no cover - IO heavy
    from flask import current_app, Response, send_file as sf, send_from_directory
    app_state = current_app.config['app_state']
    try:
        if task_id not in app_state['export_tasks']:
            return jsonify(error_response('Task not found', error_type='not_found', status=404)), 404
        task = app_state['export_tasks'][task_id]
        if task['status'] != 'completed':
            return jsonify(error_response('Export not completed', error_type='invalid_state', status=400)), 400
        if not os.path.exists(task['path']):
            return jsonify(error_response('Export file not found', error_type='not_found', status=404)), 404
        is_valid, msg, size = _validate_mp4_file(task['path'])
        if not is_valid:
            task['status'] = 'error'
            task['error'] = msg
            return jsonify(error_response(msg, error_type='validation_failed', status=400, details={'fileSize': size})), 400
        headers = {
            'Content-Disposition': f'attachment; filename="{task["filename"]}"',
            'Content-Type': 'video/mp4',
            'Content-Length': str(size),
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET',
            'Access-Control-Allow-Headers': 'Content-Type'
        }
        file_path = os.path.abspath(task['path'])
        directory = os.path.dirname(file_path)
        filename = os.path.basename(file_path)
        try:
            response = sf(task['path'], as_attachment=True, download_name=task['filename'], mimetype='video/mp4')
            for k, v in headers.items():
                response.headers[k] = v
            return response
        except Exception:
            try:
                response = send_from_directory(directory, filename, as_attachment=True, download_name=task['filename'], mimetype='video/mp4')
                for k, v in headers.items():
                    response.headers[k] = v
                return response
            except Exception:
                with open(file_path, 'rb') as fh:
                    return Response(fh.read(), mimetype='video/mp4', headers=headers)
    except Exception as e:  # noqa: BLE001
        return jsonify(error_response(f"Error downloading export: {e}", error_type='unexpected_error', status=400)), 400


@export_legacy_bp.route('/api/export/video-with-subtitles', methods=['POST'])
def export_video_with_subtitles():  # pragma: no cover - ffmpeg side-effects
    from flask import current_app
    try:
        try:
            subprocess.run(['ffmpeg', '-version'], capture_output=True, timeout=5, check=False)
        except FileNotFoundError:
            return jsonify(error_response('ffmpeg não encontrado no sistema. Instale ffmpeg para exportar.'))
        if 'video' not in request.files:
            return jsonify(error_response('Arquivo de vídeo não enviado (campo video).'))
        video_file = request.files['video']
        if not video_file.filename:
            return jsonify(error_response('Nome de arquivo de vídeo inválido.'))
        raw_payload = request.form.get('payload') or '{}'
        try:
            payload = json.loads(raw_payload)
        except Exception:
            return jsonify(error_response('Payload JSON inválido.'))
        subtitles = payload.get('subtitles') or []
        style = payload.get('style') or {}
        overlay = payload.get('overlayPosition') or {}
        effects = (style.get('effects') or {}) if isinstance(style, dict) else {}
        if not subtitles:
            return jsonify(error_response('Nenhuma legenda fornecida.'))
        upload_dir = Path(current_app.config['UPLOAD_FOLDER'])
        upload_dir.mkdir(parents=True, exist_ok=True)
        base_video_name = f"vid_{uuid.uuid4().hex[:10]}_{secure_filename(video_file.filename)}"
        input_path = upload_dir / base_video_name
        video_file.save(str(input_path))
        # Cleanup thread
        CLEANUP_TTL_SECONDS = int(effects.get('cacheTtlSeconds') or 3600)
        def _cleanup_old():  # pragma: no cover
            try:
                now = time.time()
                removed = 0
                for p in upload_dir.glob('burned_*.mp4'):
                    if removed > 50:
                        break
                    try:
                        if now - p.stat().st_mtime > CLEANUP_TTL_SECONDS:
                            p.unlink(missing_ok=True)
                            removed += 1
                    except Exception:
                        continue
                for a in upload_dir.glob('sub_*.ass'):
                    try:
                        if now - a.stat().st_mtime > CLEANUP_TTL_SECONDS:
                            a.unlink(missing_ok=True)
                    except Exception:
                        continue
            except Exception:
                pass
        threading.Thread(target=_cleanup_old, daemon=True).start()
        # Hash/cache
        video_hasher = hashlib.sha256()
        try:
            with open(input_path, 'rb') as vf:
                for chunk in iter(lambda: vf.read(1024 * 1024), b''):
                    video_hasher.update(chunk)
        except Exception:
            pass
        video_hash = video_hasher.hexdigest()
        try:
            normalized_payload = {'subtitles': subtitles, 'style': style, 'overlay': overlay}
            payload_hash = hashlib.sha256(json.dumps(normalized_payload, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()
        except Exception:
            payload_hash = uuid.uuid4().hex
        combined_hash = hashlib.sha256(f"{video_hash}:{payload_hash}".encode('utf-8')).hexdigest()
        out_name = f"burned_{combined_hash[:16]}.mp4"
        out_path = upload_dir / out_name
        if out_path.exists() and out_path.stat().st_size > 0:
            return jsonify(success_response('Export reutilizado do cache', export_filename=out_name, download_url=f"/api/export/video/burned/{out_name}", cached=True))
        # Probe dimensions
        width = height = None
        try:
            probe = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of', 'json', str(input_path)], capture_output=True, text=True, timeout=10)
            if probe.returncode == 0:
                try:
                    _pd = json.loads(probe.stdout or '{}')
                    streams = _pd.get('streams') or []
                    if streams:
                        width = streams[0].get('width')
                        height = streams[0].get('height')
                except Exception:
                    pass
        except Exception:
            pass
        if not width or not height:
            width, height = width or 1280, height or 720
        def _hex_to_ass_color(hex_color, alpha_percent=None):
            try:
                if not hex_color:
                    hex_color = '#FFFFFF'
                hc = hex_color.strip().lstrip('#')
                if len(hc) == 3:
                    hc = ''.join(c * 2 for c in hc)
                if len(hc) != 6:
                    return '&H00FFFFFF'
                r = int(hc[0:2], 16); g = int(hc[2:4], 16); b = int(hc[4:6], 16)
                if alpha_percent is None:
                    alpha = 0
                else:
                    try:
                        alpha_f = max(0, min(100, float(alpha_percent))) / 100.0
                        alpha = int(alpha_f * 255)
                    except Exception:
                        alpha = 0
                return f"&H{alpha:02X}{b:02X}{g:02X}{r:02X}"
            except Exception:
                return '&H00FFFFFF'
        base_font_size_user = style.get('fontSize')
        try:
            if base_font_size_user is not None:
                base_font_size_user = float(base_font_size_user)
        except Exception:
            base_font_size_user = None
        if base_font_size_user is None:
            base_font_size_user = 48.0
        font_size = int(max(12, round(base_font_size_user * (width / 1920.0))))
        font_name = style.get('fontFamily') or 'Arial'
        outline_w = int(style.get('outlineWidth') or 3)
        def _col(cn, alpha=None):
            return _hex_to_ass_color(style.get(cn), alpha)
        primary_color = _col('textColor') or '&H00FFFFFF'
        outline_color = _col('outlineColor') or '&H00000000'
        back_color = _hex_to_ass_color(style.get('backgroundColor') or '#000000', style.get('backgroundOpacity'))
        x_pct = float((overlay.get('xPercent', 50.0))) / 100.0
        y_pct = float((overlay.get('yPercent', 80.0))) / 100.0
        pos_x = int(width * x_pct); pos_y = int(height * y_pct)
        avg_char_px = font_size * 0.55
        target_line_chars = max(8, int(width * 0.75 / avg_char_px))
        def _wrap_text_if_needed(raw_text: str) -> str:
            if not raw_text:
                return ''
            raw = re.sub(r'<br\s*/?>', '\n', raw_text.replace('\r\n', '\n'), flags=re.IGNORECASE)
            if '\n' in raw:
                parts = [p.strip() for p in raw.split('\n') if p.strip()]
            else:
                words = raw.split()
                parts = []
                line = []
                count = 0
                for w in words:
                    wlen = len(w)
                    if count + wlen + (1 if line else 0) > target_line_chars and line:
                        parts.append(' '.join(line)); line = [w]; count = wlen
                    else:
                        line.append(w); count += wlen + (1 if line[:-1] else 0)
                if line:
                    parts.append(' '.join(line))
            return '\n'.join(parts)
        def _build_karaoke_line(sub):
            words = sub.get('words') or []
            if not words:
                return None
            line_start = sub.get('start_ms', 0)
            frags = []
            for w in words:
                w_start = w.get('start_ms', line_start); w_end = w.get('end_ms', w_start)
                if w_end < w_start:
                    w_end = w_start
                dur_cs = max(1, int((w_end - w_start)/10))
                t = w.get('text') or w.get('word') or ''
                frags.append(f"{{\\k{dur_cs}}}{t} ")
            return ''.join(frags).strip()
        ass_name = f"sub_{combined_hash[:12]}.ass"; ass_path = upload_dir / ass_name
        with open(ass_path, 'w', encoding='utf-8') as ass:
            ass.write('[Script Info]\nScriptType: v4.00+\nScaledBorderAndShadow: yes\n')
            ass.write(f'PlayResX: {width}\nPlayResY: {height}\nWrapStyle: 2\n\n[V4+ Styles]\n')
            ass.write('Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, '
                      'Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n')
            style_line = (f"Style: Default,{font_name},{font_size},{primary_color},&H000000FF,{outline_color},{back_color},"
                          f"0,0,0,0,100,100,0,0,3,{outline_w},0,5,10,10,10,1")
            ass.write(style_line + '\n\n[Events]\n')
            ass.write('Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n')
            def _fmt_ts(ms):
                if ms is None: ms = 0
                ms = max(0, int(ms))
                h = ms // 3600000; ms -= h*3600000
                m = ms // 60000; ms -= m*60000
                s = ms // 1000; cs = int((ms - s*1000)/10)
                return f"{h:d}:{m:02d}:{s:02d}.{cs:02d}"
            fade_in = int(effects.get('fadeInMs') or 0); fade_out = int(effects.get('fadeOutMs') or 0)
            karaoke_enabled = bool(effects.get('karaoke'))
            for sub in subtitles:
                start_ms = sub.get('start_ms') or sub.get('start') or 0
                end_ms = sub.get('end_ms') or sub.get('end') or (start_ms + 2000)
                if end_ms <= start_ms: end_ms = start_ms + 1
                raw_text = sub.get('text') or sub.get('line') or ''
                karaoke_line = _build_karaoke_line(sub) if karaoke_enabled else None
                wrapped = karaoke_line if karaoke_line else _wrap_text_if_needed(raw_text)
                wrapped = wrapped.replace('\n', '\\N').replace('{', '（').replace('}', '）')
                effect_tags = ''
                if fade_in or fade_out: effect_tags += f"{{\\fad({fade_in},{fade_out})}}"
                pos_tag = f"{{\\pos({pos_x},{pos_y})}}"
                final_text = f"{pos_tag}{effect_tags}{wrapped}"
                ass.write(f"Dialogue: 0,{_fmt_ts(start_ms)},{_fmt_ts(end_ms)},Default,,0,0,0,,{final_text}\n")
        sub_filter_path = ass_path.as_posix()
        sub_filter = f"subtitles=filename='{sub_filter_path}'"
        cmd = ['ffmpeg','-y','-i', str(input_path), '-vf', sub_filter, '-c:v','libx264','-preset','veryfast','-crf','20','-c:a','copy', str(out_path)]
        run = subprocess.run(cmd, capture_output=True, text=True)
        if run.returncode != 0 or not out_path.exists():
            fallback_cmd = ['ffmpeg','-y','-i', str(input_path), '-vf', sub_filter, '-c:v','libx264','-preset','veryfast','-crf','20','-c:a','aac','-b:a','192k', str(out_path)]
            fallback_run = subprocess.run(fallback_cmd, capture_output=True, text=True)
            if fallback_run.returncode != 0 or not out_path.exists():
                err_tail = (fallback_run.stderr or run.stderr or '').splitlines()[-15:]
                return jsonify(error_response('Falha ao processar export com legendas (mov/ffmpeg)', stderr=err_tail, ffmpeg_cmd=fallback_cmd))
        return jsonify(success_response('Export concluído', export_filename=out_name, download_url=f"/api/export/video/burned/{out_name}", width=width, height=height, cached=False))
    except Exception as e:  # noqa: BLE001
        return jsonify(error_response('Erro inesperado no export', exception=str(e)))


@export_legacy_bp.route('/api/export/video/burned/<path:filename>', methods=['GET'])
def download_burned_video(filename):  # pragma: no cover - small IO
    from flask import current_app
    try:
        full_path = Path(current_app.config['UPLOAD_FOLDER']) / filename
        if not full_path.exists():
            return jsonify(error_response('Arquivo não encontrado para download.'))
        return send_file(str(full_path), as_attachment=True, download_name=filename)
    except Exception as e:  # noqa: BLE001
        return jsonify(error_response('Falha no download', exception=str(e)))

__all__ = [
    'export_legacy_bp',
    'validate_export',
    'download_export',
    'export_video_with_subtitles',
    'download_burned_video'
]
