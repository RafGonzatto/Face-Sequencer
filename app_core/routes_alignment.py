"""Audio alignment routes and helper functions extracted from monolithic app.py

Goals of this module:
 - Provide a Blueprint (alignment_bp) that exposes the previous alignment
   endpoints: /api/audio/status, /api/audio/align, /api/audio/align-enhanced
 - Consolidate duplicated logic between inline endpoint implementations and
   the standalone compute_* helpers (standard + enhanced)
 - Prepare for future extraction of streaming SSE alignment (/stream) and
   cache control endpoints (cancel, invalidate) into a companion module to
   keep this file < ~1000 LOC.

Current scope purposefully excludes the very large SSE streaming endpoint and
resume/invalidation utilities; those will move into routes_alignment_stream.py
in a subsequent refactor step to keep the change set reviewable.

All state access goes through current_app.config['app_state'] instead of the
previous global app_state variable. This keeps the module factory-friendly.
"""
from __future__ import annotations
from flask import Blueprint, request, jsonify, current_app
import os, hashlib
from api_responses import success_response, error_response
from audio_cache import audio_cache, generate_cache_key
from metrics import time_block, snapshot as metrics_snapshot
from api_utils import require_audio_upload
from werkzeug.utils import secure_filename
from datetime import datetime
from typing import Any, Dict

# Lazy imports inside functions to avoid heavy startup when TEST_MODE
try:  # pragma: no cover - environment dependent
    from audio_components import audio_factory  # type: ignore
except Exception:  # pragma: no cover
    audio_factory = None  # type: ignore

alignment_bp = Blueprint("alignment", __name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_app_state() -> dict:
    return current_app.config.setdefault("app_state", {"current_project": None, "export_tasks": {}})

def _current_project() -> dict:
    state = _get_app_state()
    if state.get("current_project") is None:
        # Create empty project container lazily (minimal keys used here)
        state["current_project"] = {
            "text": "",
            "audio_file": None,
            "timing_mode": "manual",
            "sequence": [],
            "last_alignment": None,
            "frame_states": [],
            "fps": 30.0,
        }
    return state["current_project"]

def _audio_aligner():  # pragma: no cover - thin wrapper
    if not audio_factory:
        return None
    try:
        return audio_factory.get_audio_aligner(language="pt-BR")
    except Exception:
        return None

def _normalize_alignment_tokens(tokens):
    sequence = []
    for token in tokens or []:
        token_dict = token.copy() if isinstance(token, dict) else dict(token)
        if (
            "start_ms" in token_dict
            and "end_ms" in token_dict
            and "duration_ms" not in token_dict
        ):
            token_dict["duration_ms"] = token_dict["end_ms"] - token_dict["start_ms"]
        sequence.append(token_dict)
    return sequence

def _apply_alignment_state_from_payload(text: str, audio_filename: str, payload: dict) -> None:
    project = _current_project()
    stats = payload.get("stats", {}) or {}
    alignment_meta = payload.get("alignment", {}) or {}
    alignment_stats = alignment_meta.get("stats", {}) or {}
    method = (
        stats.get("method")
        or alignment_meta.get("method")
        or alignment_stats.get("method")
        or "unknown"
    )
    total_duration = (
        stats.get("total_duration_ms")
        or alignment_meta.get("total_duration_ms")
        or alignment_stats.get("audio_ms")
        or 0
    )
    confidence = (
        alignment_stats.get("avg_confidence")
        or stats.get("avg_confidence")
        or alignment_meta.get("confidence_score")
        or 0.0
    )
    project["text"] = text
    project["audio_alignment"] = {
        "filename": audio_filename,
        "alignment_method": method,
        "total_duration_ms": total_duration,
        "confidence_score": confidence,
        "created_at": datetime.utcnow().isoformat(),
    }

# ---------------------------------------------------------------------------
# Core compute functions (standard + enhanced)
# ---------------------------------------------------------------------------

def compute_standard_alignment(audio_filename: str, text: str, language: str = "pt-BR", *, use_cache: bool = True) -> dict:
    from audio_exceptions import AlignmentError
    if not audio_filename:
        raise AlignmentError("No audio filename provided", details={"field": "audio_filename"})
    audio_folder = current_app.config["AUDIO_FOLDER"]
    audio_path = os.path.join(audio_folder, audio_filename)
    if not os.path.exists(audio_path):
        raise AlignmentError("Audio file not found", details={"filename": audio_filename})
    aligner = _audio_aligner()
    if not aligner:
        raise AlignmentError("Audio aligner not available", details={"stage": "initialize"})
    cache_key = file_hash = params_signature = None
    cache_params = {
        "operation": "align",
        "language": language,
        "text_hash": hashlib.sha256(text.strip().encode("utf-8")).hexdigest(),
    }
    if use_cache:
        cache_key, file_hash, params_signature = generate_cache_key(audio_path, cache_params, namespace="alignment")
        cached_response = audio_cache.get(cache_key)
        if cached_response:
            cached_message = cached_response.get("message", "Audio alignment result retrieved from cache")
            cached_response["cached"] = True
            if "(cached)" not in cached_message.lower():
                cached_response["message"] = f"{cached_message} (cached)"
            _apply_alignment_state_from_payload(text, audio_filename, cached_response)
            return cached_response
    from audio_error_handling import with_timeout
    @with_timeout(timeout_seconds=300)
    def _run():
        result = aligner.align_audio_to_text(audio_path, text, language=language)
        if not result:
            from audio_exceptions import AlignmentError
            raise AlignmentError("Alignment failed - no result returned", details={"text": text[:100]})
        return {
            "success": True,
            "language": result.language,
            "sample_rate": result.sample_rate,
            "method": "energy-based",
            "tokens": [
                {
                    "type": t.type.value,
                    "text": t.text,
                    "viseme": t.viseme,
                    "start_ms": t.start_ms,
                    "end_ms": t.end_ms,
                    "confidence": t.confidence,
                    "lang": t.lang,
                }
                for t in result.tokens
            ],
            "stats": {
                "audio_ms": result.stats.audio_ms,
                "drift_ms": result.stats.drift_ms,
                "unaligned_count": result.stats.unaligned_count,
                "avg_confidence": result.stats.avg_confidence,
                "pause_count": result.stats.pause_count,
            },
            "total_duration_ms": result.stats.audio_ms,
        }
    with time_block("alignment_time_ms"):
        alignment_dict = _run()
    tokens = _normalize_alignment_tokens(alignment_dict.get("tokens", []))
    payload = {
        "success": True,
        "alignment": alignment_dict,
        "sequence": tokens,
        "stats": {
            "total_tokens": len(tokens),
            "word_tokens": sum(1 for t in tokens if t.get("type") == "word"),
            "gap_tokens": sum(1 for t in tokens if t.get("type") == "gap"),
            "total_duration_ms": alignment_dict.get("total_duration_ms", 0),
            "method": alignment_dict.get("method", "energy-based"),
        },
        "message": "Audio alignment completed successfully",
        "cached": False,
    }
    _apply_alignment_state_from_payload(text, audio_filename, payload)
    if use_cache and cache_key is not None:
        audio_cache.set(cache_key, payload, file_hash, params_signature)
    return payload

def compute_enhanced_alignment(audio_filename: str, text: str, *, language: str = "pt-BR", fps: float = 30.0, method: str = "auto", use_cache: bool = True) -> dict:
    from audio_exceptions import AlignmentError
    if not audio_filename:
        raise AlignmentError("No audio filename provided", details={"field": "audio_filename"})
    audio_path = os.path.join(current_app.config["AUDIO_FOLDER"], audio_filename)
    if not os.path.exists(audio_path):
        raise AlignmentError("Audio file not found", details={"filename": audio_filename})
    aligner = _audio_aligner()
    if not aligner:
        raise AlignmentError("Audio aligner not available", details={"stage": "initialize"})
    if not hasattr(aligner, "align_audio_to_text_enhanced"):
        raise AlignmentError("Enhanced alignment method not available", details={"stage": "initialize"})
    cache_key = file_hash = params_signature = None
    cache_params = {
        "operation": "align_enhanced",
        "language": language,
        "fps": float(fps),
        "method": method,
        "text_hash": hashlib.sha256(text.strip().encode("utf-8")).hexdigest(),
    }
    if use_cache:
        cache_key, file_hash, params_signature = generate_cache_key(audio_path, cache_params, namespace="alignment_enhanced")
        cached_response = audio_cache.get(cache_key)
        if cached_response:
            cached_message = cached_response.get("message", "Enhanced alignment retrieved from cache")
            cached_response["cached"] = True
            if "(cached)" not in cached_message.lower():
                cached_response["message"] = f"{cached_message} (cached)"
            _apply_alignment_state_from_payload(text, audio_filename, cached_response)
            return cached_response
    from audio_error_handling import with_timeout
    @with_timeout(timeout_seconds=360)
    def _run():
        result, timeline, frame_states = aligner.align_audio_to_text_enhanced(audio_path, text, language=language, fps=fps, method=method)
        if not result:
            from audio_exceptions import AlignmentError
            raise AlignmentError("Enhanced alignment failed - no result returned", details={"text": text[:100]})
        return {
            "success": True,
            "method": "enhanced",
            "language": result.language,
            "sample_rate": result.sample_rate,
            "fps": fps,
            "tokens": [
                {
                    "type": t.type.value,
                    "text": t.text,
                    "viseme": t.viseme,
                    "start_ms": t.start_ms,
                    "end_ms": t.end_ms,
                    "confidence": t.confidence,
                    "lang": t.lang,
                    "duration_ms": t.end_ms - t.start_ms,
                }
                for t in result.tokens
            ],
            "timeline": [
                {
                    "word": wt.word,
                    "start_time": wt.start_time,
                    "end_time": wt.end_time,
                    "start_frame": wt.start_frame,
                    "end_frame": wt.end_frame,
                    "start_frame_float": wt.start_frame_float,
                    "end_frame_float": wt.end_frame_float,
                    "start_offset": wt.start_offset,
                    "end_offset": wt.end_offset,
                    "confidence": wt.confidence,
                    "duration": wt.duration,
                }
                for wt in (timeline or [])
            ],
            "frame_states": [
                {
                    "frame_number": fs.frame_number,
                    "timestamp": fs.timestamp,
                    "active_word": fs.active_word,
                    "word_progress": fs.word_progress,
                    "opacity": fs.opacity,
                    "viseme": fs.viseme,
                    "confidence": fs.confidence,
                }
                for fs in (frame_states or [])
            ],
            "stats": {
                "audio_ms": result.stats.audio_ms,
                "drift_ms": result.stats.drift_ms,
                "unaligned_count": result.stats.unaligned_count,
                "avg_confidence": result.stats.avg_confidence,
                "pause_count": result.stats.pause_count,
            },
            "total_duration_ms": result.stats.audio_ms,
            "enhancement_features": {
                "sub_frame_timing": True,
                "forced_alignment": True,
                "enhanced_silence_detection": True,
                "confidence_scoring": True,
                "frame_synchronization": True,
            },
        }
    with time_block("alignment_time_ms"):
        alignment_dict = _run()
    tokens = _normalize_alignment_tokens(alignment_dict.get("tokens", []))
    frame_states = alignment_dict.get("frame_states", [])
    # Persist for downstream consumers
    project = _current_project()
    project["last_alignment"] = alignment_dict
    project["frame_states"] = frame_states
    project["fps"] = alignment_dict.get("fps") or fps
    payload = {
        "success": True,
        "alignment": alignment_dict,
        "sequence": tokens,
        "stats": {
            "total_tokens": len(tokens),
            "word_tokens": sum(1 for t in tokens if t.get("type") == "word"),
            "gap_tokens": sum(1 for t in tokens if t.get("type") == "gap"),
            "total_duration_ms": alignment_dict.get("total_duration_ms", 0),
            "total_frames": len(frame_states),
            "fps": fps,
            "method": "enhanced",
            "avg_confidence": alignment_dict.get("stats", {}).get("avg_confidence", 0.0),
            "timing_precision": "sub-frame",
        },
        "message": f"Enhanced audio alignment completed successfully with {fps} FPS precision",
        "cached": False,
    }
    _apply_alignment_state_from_payload(text, audio_filename, payload)
    if use_cache and cache_key is not None:
        audio_cache.set(cache_key, payload, file_hash, params_signature)
    return payload

# ---------------------------------------------------------------------------
# Status Endpoint
# ---------------------------------------------------------------------------
@alignment_bp.route("/api/audio/status", methods=["GET"])
def audio_status():
    aligner = _audio_aligner()
    enhanced = bool(aligner and getattr(aligner, "use_enhanced", False))
    available = bool(aligner)
    return jsonify(
        success_response(
            "Audio alignment system status",
            available=available,
            enhanced_available=enhanced,
            language="pt-BR" if available else None,
            supported_formats=list(current_app.config["ALLOWED_AUDIO_EXTENSIONS"]),
            features={
                "basic_alignment": available,
                "enhanced_silence_detection": enhanced,
                "forced_alignment": enhanced,
                "sub_frame_timing": enhanced,
                "confidence_scoring": enhanced,
                "frame_synchronization": enhanced,
            },
        )
    )

# ---------------------------------------------------------------------------
# Upload Endpoint (migrated minimal version)
# ---------------------------------------------------------------------------
@alignment_bp.route("/api/audio/upload", methods=["POST"])
@require_audio_upload("audio")
def upload_audio(audio):  # pragma: no cover - I/O heavy
    from audio_error_handling import handle_audio_errors, validate_audio_content, detect_speech_activity
    from audio_exceptions import AlignmentError
    aligner = _audio_aligner()
    if not aligner:
        raise AlignmentError("Audio aligner not available", details={"phase": "precheck"})
    @handle_audio_errors()
    def _process(audio_file):
        audio_folder = current_app.config["AUDIO_FOLDER"]
        os.makedirs(audio_folder, exist_ok=True)
        from time import time as _now
        safe_name = secure_filename(audio_file.filename)
        unique_filename = f"{int(_now())}_{safe_name}"
        audio_path = os.path.join(audio_folder, unique_filename)
        audio_file.save(audio_path)
        meta = validate_audio_content(audio_path)
        speech_info = detect_speech_activity(audio_path)
        audio_data, sample_rate = aligner.preprocess_audio(audio_path)
        stored_hash = hashlib.sha1(open(audio_path, "rb").read()).hexdigest()  # lightweight alt to existing helper
        audio_cache.invalidate_by_file_hash(stored_hash)
        info = {
            "filename": unique_filename,
            "original_filename": audio_file.filename,
            "duration_ms": meta["duration_ms"],
            "sample_rate": sample_rate,
            "samples": len(audio_data),
            "speech_info": speech_info,
            "file_hash": stored_hash,
        }
        return jsonify(success_response("Audio uploaded", **info))
    return _process(audio)

# ---------------------------------------------------------------------------
# Alignment POST Endpoints
# ---------------------------------------------------------------------------
@alignment_bp.route("/api/audio/align", methods=["POST"])
def align_audio_endpoint():
    from audio_error_handling import handle_audio_errors, AudioFallbackHandler
    from audio_exceptions import AlignmentError
    @handle_audio_errors(fallback_handler=AudioFallbackHandler.fallback_to_manual_timing)
    def _impl():
        data = request.get_json() or {}
        text = data.get("text", "")
        if not text.strip():
            raise AlignmentError("No text provided for alignment", details={"phase": "validation"})
        filename = data.get("filename")
        language = data.get("language", "pt-BR")
        payload = compute_standard_alignment(filename, text, language=language, use_cache=True)
        # Update project sequence
        project = _current_project()
        project.update({
            "audio_file": filename,
            "timing_mode": "audio_driven",
            "sequence": payload.get("sequence", []),
            "text": text,
        })
        return jsonify(
            success_response(
                payload.get("message", "Audio alignment completed successfully"),
                **{k: v for k, v in payload.items() if k not in {"success", "message"}}
            )
        )
    return _impl()

@alignment_bp.route("/api/audio/align-enhanced", methods=["POST"])
def align_audio_enhanced_endpoint():
    from audio_error_handling import handle_audio_errors, AudioFallbackHandler
    from audio_exceptions import AlignmentError
    @handle_audio_errors(fallback_handler=AudioFallbackHandler.fallback_to_manual_timing)
    def _impl():
        data = request.get_json() or {}
        text = data.get("text", "")
        if not text.strip():
            raise AlignmentError("No text provided for alignment", details={"phase": "validation"})
        filename = data.get("filename")
        language = data.get("language", "pt-BR")
        fps = float(data.get("fps", 30.0))
        method = data.get("method", "auto")
        aligner = _audio_aligner()
        if not aligner or not hasattr(aligner, "align_audio_to_text_enhanced"):
            # Fallback to standard
            return align_audio_endpoint()
        payload = compute_enhanced_alignment(filename, text, language=language, fps=fps, method=method, use_cache=True)
        project = _current_project()
        project.update({
            "audio_file": filename,
            "timing_mode": "audio_driven",
            "sequence": payload.get("sequence", []),
            "text": text,
        })
        return jsonify(
            success_response(
                payload.get("message", "Enhanced audio alignment completed"),
                **{k: v for k, v in payload.items() if k not in {"success", "message"}}
            )
        )
    return _impl()

__all__ = [
    "alignment_bp",
    "compute_standard_alignment",
    "compute_enhanced_alignment",
]
