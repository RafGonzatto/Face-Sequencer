"""Streaming (SSE) enhanced audio alignment endpoints extracted from monolithic app.py

This module isolates the long /api/audio/align-enhanced/stream endpoint plus the
lightweight control/cache endpoints (cancel, cache/invalidate) so that
`routes_alignment.py` remains focused on non-streaming alignment concerns.

Design notes:
 - Reuses helper functions from routes_alignment for aligner access when needed.
 - Avoids global constants by computing feature availability on demand.
 - Maintains original event payload schema to avoid breaking the frontend
   (video_editor.js listens for identical event names: start, precheck, decode,
    transcribe, tokens_partial, align, enhance, build_sequence, complete,
    cancelled, error, heartbeat, fallback, resume).
 - Keeps in-memory job tracking + tiny resume cache (best‑effort LRU of size 5)
   exactly as before, but namespaced on the Flask `app` object for continuity.

Future improvements (deferred):
 - Unify resume cache + audio_cache logic (persist resume tokens across process).
 - Add authentication / rate limiting hooks for long running jobs.
 - Factor token smoothing + silence heuristics into reusable utility helpers.
"""
from __future__ import annotations

from flask import Blueprint, request, current_app, Response, stream_with_context, jsonify
from api_responses import success_response, error_response
from typing import Dict, Any
import os, json, datetime, hashlib, time, uuid

from .routes_alignment import _audio_aligner  # reuse minimal helper

stream_alignment_bp = Blueprint("alignment_stream", __name__)


def _availability():
    """Compute (basic, enhanced) availability lazily to avoid stale globals."""
    aligner = _audio_aligner()
    audio_available = bool(aligner)
    enhanced_available = bool(audio_available and getattr(aligner, "use_enhanced", False))
    return audio_available, enhanced_available, aligner


PHASE_WEIGHTS = {
    'start': 0,
    'precheck': 5,
    'load_audio': 10,
    'decode': 25,
    'resume': 50,  # synthetic phase when resuming from cached tokens
    'transcribe': 55,
    'align': 75,
    'enhance': 85,
    'build_sequence': 95,
    'complete': 100,
}


def _event(phase: str, data: Dict[str, Any] | None = None) -> str:
    pct = PHASE_WEIGHTS.get(phase, min(PHASE_WEIGHTS.values()))
    payload = {
        'event': phase,
        'data': {**(data or {}), 'progress_percent': pct},
        'timestamp': datetime.datetime.utcnow().isoformat() + 'Z'
    }
    return f"data: {json.dumps(payload)}\n\n"


@stream_alignment_bp.route('/api/audio/align-enhanced/stream', methods=['POST'])
def align_audio_enhanced_stream():  # pragma: no cover - streaming path / I/O heavy
    """Server-Sent Events (SSE) streaming variant of enhanced alignment.

    Preserves legacy behavior. If enhanced path is unavailable, falls back to
    standard alignment endpoint logic by internally invoking the non-stream
    endpoint from `routes_alignment`.
    """
    from audio_exceptions import AlignmentError
    from .routes_alignment import align_audio_endpoint  # local import to avoid cycles

    # Job bookkeeping containers (lazily attached to app instance)
    ACTIVE_ALIGNMENT_JOBS: Dict[str, Dict[str, Any]] = getattr(current_app, '_active_alignment_jobs', {})  # type: ignore[attr-defined]
    setattr(current_app, '_active_alignment_jobs', ACTIVE_ALIGNMENT_JOBS)
    RESUME_CACHE: Dict[str, Dict[str, Any]] = getattr(current_app, '_alignment_resume_cache', {})  # type: ignore[attr-defined]
    setattr(current_app, '_alignment_resume_cache', RESUME_CACHE)
    RESUME_CACHE_TTL_SECONDS = 15 * 60  # 15 minutes

    audio_available, enhanced_available, aligner = _availability()

    @stream_with_context
    def generate():  # noqa: PLR0912 - linear streaming phases retained
        job_id = f"aln_{uuid.uuid4().hex[:10]}"
        ACTIVE_ALIGNMENT_JOBS[job_id] = {'cancel': False, 'started': time.time()}
        last_heartbeat = time.time()
        try:
            # Opportunistic cleanup of stale resume entries
            try:  # pragma: no cover - best effort
                now_ts = time.time()
                stale = [k for k, v in RESUME_CACHE.items() if (now_ts - v.get('created', now_ts)) > RESUME_CACHE_TTL_SECONDS]
                for k in stale:
                    RESUME_CACHE.pop(k, None)
            except Exception:
                pass

            body = request.get_json(silent=True) or {}
            audio_filename = body.get('filename')
            text = body.get('text', '')
            language = body.get('language', 'pt-BR')
            fps = float(body.get('fps', 30.0))
            method = body.get('method', 'auto')
            precision_mode = body.get('precision_mode', 'balanced')  # balanced|maximum|fast
            resume_from_tokens = int(body.get('resume_from_tokens', 0) or 0)
            resume_cache_key = body.get('resume_cache_key')

            # Deterministic cache key for resume (NOT audio_cache)
            cache_basis = f"{audio_filename}|{fps}|{language}|{method}|{len(text)}|{hash(text)}"
            cache_key = hashlib.sha1(cache_basis.encode('utf-8')).hexdigest()[:20]
            yield _event('start', {'message': 'Enhanced alignment starting', 'job_id': job_id, 'cache_key': cache_key})
            yield _event('precheck', {'enhanced_available': enhanced_available, 'audio_alignment_available': audio_available})

            if ACTIVE_ALIGNMENT_JOBS[job_id]['cancel']:
                yield _event('cancelled', {'job_id': job_id, 'phase': 'precheck'})
                return
            if not audio_available:
                raise AlignmentError('Audio alignment system not available', details={'phase': 'precheck'})
            if not audio_filename:
                raise AlignmentError('No audio filename provided', details={'phase': 'precheck'})
            if not text.strip():
                raise AlignmentError('No text provided', details={'phase': 'precheck'})

            audio_path = os.path.join(current_app.config['AUDIO_FOLDER'], audio_filename)
            if not os.path.exists(audio_path):
                raise AlignmentError('Audio file not found', details={'filename': audio_filename, 'phase': 'precheck'})

            yield _event('load_audio', {'filename': audio_filename})
            if not aligner:
                raise AlignmentError('Audio aligner not available', details={'phase': 'precheck'})
            if not enhanced_available or not hasattr(aligner, 'align_audio_to_text_enhanced'):
                # Fallback: call standard endpoint inside an internal request ctx
                yield _event('fallback', {'reason': 'enhanced_unavailable'})
                with current_app.test_request_context(json={'filename': audio_filename, 'text': text, 'language': language, 'fps': fps, 'method': method}):
                    standard_resp = align_audio_endpoint()
                yield _event('complete', {'fallback': True, 'result': standard_resp.get_json() if hasattr(standard_resp, 'get_json') else None})
                ACTIVE_ALIGNMENT_JOBS.pop(job_id, None)
                return

            if ACTIVE_ALIGNMENT_JOBS[job_id]['cancel']:
                yield _event('cancelled', {'job_id': job_id, 'phase': 'decode'})
                ACTIVE_ALIGNMENT_JOBS.pop(job_id, None)
                return

            tokens_full = []
            frame_states = []
            alignment_result = None
            used_cache = False

            if resume_cache_key and resume_cache_key in RESUME_CACHE:
                cached = RESUME_CACHE[resume_cache_key]
                tokens_full = cached.get('tokens_full', [])
                frame_states = cached.get('frame_states', [])
                alignment_result = cached.get('alignment_result')
                used_cache = True
                yield _event('resume', {'job_id': job_id, 'cache_key': cache_key, 'resume_from_tokens': resume_from_tokens, 'cached_tokens': len(tokens_full)})
            else:
                yield _event('decode', {'message': 'Decoding & preparing models', 'job_id': job_id})
                try:
                    # Underlying enhanced alignment call
                    alignment_result, timeline, frame_states = aligner.align_audio_to_text_enhanced(
                        audio_path, text, language=language, fps=fps, method=method
                    )
                except Exception as dec_err:  # noqa: BLE001
                    raise AlignmentError(f'Enhanced alignment failed early: {dec_err}', details={'phase': 'decode'})

                tokens_full = getattr(alignment_result, 'tokens', []) or []

                # Optional smoothing for maximum precision
                if precision_mode == 'maximum':
                    try:  # pragma: no cover - heuristic, non critical
                        smoothed = []
                        window = 3
                        for i, tk in enumerate(tokens_full):
                            if not hasattr(tk, 'start_ms') or not hasattr(tk, 'end_ms'):
                                smoothed.append(tk)
                                continue
                            start_vals = [tokens_full[j].start_ms for j in range(max(0, i-window), min(len(tokens_full), i+window+1)) if hasattr(tokens_full[j], 'start_ms')]
                            end_vals = [tokens_full[j].end_ms for j in range(max(0, i-window), min(len(tokens_full), i+window+1)) if hasattr(tokens_full[j], 'end_ms')]
                            if start_vals and end_vals:
                                try:
                                    new_tk = tk.__class__(**tk.__dict__)
                                except Exception:  # noqa: BLE001
                                    new_tk = tk
                                new_tk.start_ms = int(sum(start_vals)/len(start_vals))
                                new_tk.end_ms = int(sum(end_vals)/len(end_vals))
                                if new_tk.end_ms < new_tk.start_ms:
                                    new_tk.end_ms = new_tk.start_ms + 1
                                smoothed.append(new_tk)
                            else:
                                smoothed.append(tk)
                        tokens_full = smoothed
                    except Exception:  # noqa: BLE001
                        pass

                # Silence / unusable heuristics (unchanged)
                try:  # pragma: no cover - heuristic
                    stats_obj = getattr(alignment_result, 'stats', None)
                    audio_ms = getattr(stats_obj, 'audio_ms', None) if stats_obj else None
                    avg_conf = getattr(stats_obj, 'avg_confidence', None) if stats_obj else None
                    from audio_exceptions import AlignmentError as _AE
                    if (audio_ms and audio_ms > 5000) and len(tokens_full) < 3:
                        raise _AE('Audio aparentemente silencioso (poucos tokens)', details={'phase': 'decode', 'reason': 'low_tokens'})
                    if (audio_ms and audio_ms > 8000) and (avg_conf is not None and avg_conf < 0.02):
                        raise _AE('Áudio com confiança muito baixa (possível silêncio)', details={'phase': 'decode', 'reason': 'low_confidence', 'avg_confidence': avg_conf})
                except AlignmentError:
                    raise
                except Exception:  # noqa: BLE001
                    pass

            # Heartbeat helper
            def _heartbeat():
                nonlocal last_heartbeat
                now = time.time()
                if now - last_heartbeat > 8:
                    last_heartbeat = now
                    return True
                return False

            start_index = 0
            if 0 < resume_from_tokens < len(tokens_full):
                start_index = resume_from_tokens

            if precision_mode == 'fast':
                chunk_size = 35
            elif precision_mode == 'maximum':
                chunk_size = 15
            else:
                chunk_size = 20

            # Stream token chunks
            for i in range(start_index, len(tokens_full), chunk_size):
                if ACTIVE_ALIGNMENT_JOBS[job_id]['cancel']:
                    yield _event('cancelled', {'job_id': job_id, 'phase': 'transcribe'})
                    ACTIVE_ALIGNMENT_JOBS.pop(job_id, None)
                    return
                subset = tokens_full[i:i+chunk_size]
                subset_json = [
                    {
                        'type': t.type.value,
                        'text': t.text,
                        'start_ms': t.start_ms,
                        'end_ms': t.end_ms,
                        'confidence': t.confidence,
                        'lang': t.lang,
                    } for t in subset
                ]
                phase_evt = 'transcribe' if (i == 0 and start_index == 0) else 'tokens_partial'
                yield _event(phase_evt, {
                    'message': 'Transcribing & tokenizing' if i == 0 else 'More tokens',
                    'chunk_index': i // chunk_size,
                    'token_chunk': subset_json,
                    'sent_tokens': min(i+chunk_size, len(tokens_full)),
                    'total_tokens': len(tokens_full),
                    'job_id': job_id,
                    'cache_key': cache_key,
                    'start_index': i,
                    'resume': used_cache or (start_index > 0),
                    'precision_mode': precision_mode
                })
                if _heartbeat():
                    yield _event('heartbeat', {'job_id': job_id, 'uptime_ms': int((time.time()-ACTIVE_ALIGNMENT_JOBS[job_id]['started'])*1000)})

            if ACTIVE_ALIGNMENT_JOBS[job_id]['cancel']:
                yield _event('cancelled', {'job_id': job_id, 'phase': 'align'})
                ACTIVE_ALIGNMENT_JOBS.pop(job_id, None)
                return

            yield _event('align', {
                'message': 'Refining alignment',
                'language': getattr(alignment_result, 'language', language) if alignment_result else language,
                'job_id': job_id,
                'precision_mode': precision_mode
            })

            if ACTIVE_ALIGNMENT_JOBS[job_id]['cancel']:
                yield _event('cancelled', {'job_id': job_id, 'phase': 'enhance'})
                ACTIVE_ALIGNMENT_JOBS.pop(job_id, None)
                return

            yield _event('enhance', {'message': 'Applying enhancement & frame states', 'job_id': job_id, 'precision_mode': precision_mode})

            frame_states_json = [
                {
                    'frame_number': fs.frame_number,
                    'timestamp': fs.timestamp,
                    'active_word': fs.active_word,
                    'word_progress': fs.word_progress,
                    'opacity': fs.opacity,
                    'viseme': fs.viseme,
                    'confidence': fs.confidence
                } for fs in (frame_states or [])
            ]
            tokens_json = [
                {
                    'type': t.type.value,
                    'text': t.text,
                    'viseme': t.viseme,
                    'start_ms': t.start_ms,
                    'end_ms': t.end_ms,
                    'confidence': t.confidence,
                    'lang': t.lang,
                    'duration_ms': t.end_ms - t.start_ms
                } for t in (getattr(alignment_result, 'tokens', []) or [])
            ]
            result_dict = {
                'method': 'enhanced',
                'language': getattr(alignment_result, 'language', language) if alignment_result else language,
                'sample_rate': getattr(alignment_result, 'sample_rate', None) if alignment_result else None,
                'fps': fps,
                'tokens': tokens_json,
                'frame_states': frame_states_json,
                'stats': {
                    'audio_ms': getattr(getattr(alignment_result, 'stats', None), 'audio_ms', None) if alignment_result else None,
                    'avg_confidence': getattr(getattr(alignment_result, 'stats', None), 'avg_confidence', None) if alignment_result else None,
                },
                'total_duration_ms': getattr(getattr(alignment_result, 'stats', None), 'audio_ms', None) if alignment_result else None
            }

            if ACTIVE_ALIGNMENT_JOBS[job_id]['cancel']:
                yield _event('cancelled', {'job_id': job_id, 'phase': 'build_sequence'})
                ACTIVE_ALIGNMENT_JOBS.pop(job_id, None)
                return

            yield _event('build_sequence', {'message': 'Finalizing sequence', 'token_count': len(tokens_json), 'job_id': job_id, 'precision_mode': precision_mode})
            yield _event('complete', {'success': True, 'alignment': result_dict, 'job_id': job_id, 'cache_key': cache_key, 'precision_mode': precision_mode})

            # Populate small resume cache (size limit = 5)
            try:  # pragma: no cover - best effort
                RESUME_CACHE[cache_key] = {
                    'alignment_result': alignment_result,
                    'tokens_full': tokens_full,
                    'frame_states': frame_states,
                    'created': time.time(),
                    'audio_filename': audio_filename,
                    'fps': fps,
                    'language': language,
                }
                if len(RESUME_CACHE) > 5:
                    oldest_key = sorted(RESUME_CACHE.items(), key=lambda kv: kv[1].get('created', 0))[0][0]
                    if oldest_key != cache_key:
                        RESUME_CACHE.pop(oldest_key, None)
            except Exception:  # noqa: BLE001
                pass
            ACTIVE_ALIGNMENT_JOBS.pop(job_id, None)
        except AlignmentError as ae:  # noqa: BLE001
            yield _event('error', {'error': str(ae), 'details': getattr(ae, 'details', {}), 'error_type': 'alignment_error'})
        except Exception as e:  # noqa: BLE001
            yield _event('error', {'error': str(e), 'error_type': 'unexpected_error'})

    return Response(generate(), mimetype='text/event-stream')


@stream_alignment_bp.route('/api/audio/align-enhanced/cancel', methods=['POST'])
def cancel_alignment_stream():  # pragma: no cover - small control path
    try:
        data = request.get_json(silent=True) or {}
        job_id = data.get('job_id')
        ACTIVE_ALIGNMENT_JOBS: Dict[str, Dict[str, Any]] = getattr(current_app, '_active_alignment_jobs', {})  # type: ignore[attr-defined]
        if job_id in ACTIVE_ALIGNMENT_JOBS:
            ACTIVE_ALIGNMENT_JOBS[job_id]['cancel'] = True
            return jsonify(success_response('Cancellation requested', job_id=job_id))
        return jsonify(error_response('Job not found', error_type='not_found', status=404)), 404
    except Exception as e:  # noqa: BLE001
        return jsonify(error_response(str(e), error_type='unexpected_error', status=500)), 500


@stream_alignment_bp.route('/api/audio/align-enhanced/cache/invalidate', methods=['POST'])
def invalidate_alignment_resume_cache():  # pragma: no cover - maintenance util
    """Invalidate resume cache entries.

    POST JSON body options:
      cache_key: (optional) specific cache key to remove
      all: true (optional) remove all entries
    """
    try:
        data = request.get_json(silent=True) or {}
        cache_key = data.get('cache_key')
        remove_all = bool(data.get('all'))
        RESUME_CACHE: Dict[str, Dict[str, Any]] = getattr(current_app, '_alignment_resume_cache', {})  # type: ignore[attr-defined]
        removed: list[str] = []
        if remove_all:
            removed = list(RESUME_CACHE.keys())
            RESUME_CACHE.clear()
        elif cache_key:
            if cache_key in RESUME_CACHE:
                RESUME_CACHE.pop(cache_key, None)
                removed.append(cache_key)
        else:
            return jsonify(error_response('Provide cache_key or all=true', error_type='bad_request', status=400)), 400
        return jsonify(success_response('Cache invalidation complete', removed=removed, remaining=len(RESUME_CACHE)))
    except Exception as e:  # noqa: BLE001
        return jsonify(error_response(str(e), error_type='unexpected_error', status=500)), 500


__all__ = [
    'stream_alignment_bp',
]
