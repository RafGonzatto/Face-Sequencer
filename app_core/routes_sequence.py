"""Sequence building and timing correction blueprint extracted from monolithic app.py.

Provides:
  - validate_and_correct_frame_timing: robust frame timing normalization
  - tokenize_word_enhanced: text/viseme token mapping with special token support
  - build_text_driven_sequence_enhanced: primary sequence constructor with anti-truncation safeguards
  - /api/sequence/build-from-audio endpoint (was /api/sequence/build-from-audio in app.py)

The functions are intentionally kept importable so tests that previously
did `from app import build_text_driven_sequence_enhanced` can still work via
re-export shims in app.py.
"""
from __future__ import annotations

from flask import Blueprint, request, jsonify, current_app

# NOTE: Use a distinct blueprint name to avoid clashing with the legacy
# 'sequence' blueprint defined in sequence_endpoints.py (which provides
# /api/sequence/frame/<id>, update, reorder, delete endpoints). The previous
# refactor unintentionally used the same name, preventing those routes from
# registering (404 in Selenium tests). We rename here and keep a backward
# compatible alias 'sequence_bp' so any imports expecting sequence_bp continue
# to function, while the real blueprint name is unique.
sequence_build_bp = Blueprint("sequence_build", __name__)
sequence_bp = sequence_build_bp  # backward compatibility alias


def validate_and_correct_frame_timing(frame_states, audio_duration_ms=None, fps: float = 30.0):  # noqa: D401
    """Apply deterministic timing normalization to every frame.

    Always enforces perfectly uniform frame timing (1/fps seconds) and
    derives precise timestamps to prevent long‑duration drift.
    """
    if not frame_states:
        return frame_states

    print(f"🎯 ROBUST TIMING CORRECTION: Processing {len(frame_states)} frames for {fps} FPS")
    target_frame_duration_ms = 1000.0 / fps

    corrected_frames = []
    for i, frame in enumerate(frame_states):
        corrected = frame.copy()
        corrected["ms_original"] = frame.get("ms", target_frame_duration_ms)
        if "timestamp" in frame:
            corrected["timestamp_original"] = frame["timestamp"]
        corrected["ms"] = target_frame_duration_ms
        corrected["timestamp"] = round(i / fps, 6)
        if i and i % 1000 == 0:
            expected = i / fps
            drift_ms = abs(corrected["timestamp"] - expected) * 1000
            if drift_ms > 1.0:
                print(f"⚠️  WARNING: Drift detected at frame {i}: {drift_ms:.2f}ms - correcting")
                corrected["timestamp"] = round(i / fps, 6)
        corrected_frames.append(corrected)

    total_frames = len(corrected_frames)
    expected_duration = total_frames / fps
    actual_duration = corrected_frames[-1]["timestamp"] if corrected_frames else 0
    final_drift_ms = abs(actual_duration - expected_duration) * 1000
    print("✅ CORRECTION COMPLETE:")
    print(f"   Total frames: {total_frames}")
    print(f"   Expected duration: {expected_duration:.3f}s")
    print(f"   Actual duration: {actual_duration:.3f}s")
    print(f"   Final timing error: {final_drift_ms:.1f}ms")
    return corrected_frames


def tokenize_word_enhanced(word, special_tokens, is_word_start: bool = False, project=None):
    """Enhanced tokenizer with special token matching and vowel variants."""
    tokens = []
    i = 0
    letter_map = project.get('letter_map', {}) if project else {}
    fallback_image = project.get('fallback_image_abs') or project.get('fallback_image') if project else None

    while i < len(word):
        matched = False
        if i + 1 < len(word):
            digraph = word[i:i+2].upper()
            if digraph in special_tokens:
                tokens.append({'token': word[i:i+2], 'img': special_tokens[digraph]})
                i += 2
                matched = True
        if not matched:
            char = word[i]
            char_upper = char.upper()
            vowel_map = {'Á': 'A', 'À': 'A', 'Ã': 'A', 'Â': 'A', 'É': 'E', 'È': 'E', 'Ê': 'E', 'Í': 'I', 'Ì': 'I', 'Î': 'I', 'Ó': 'O', 'Ò': 'O', 'Õ': 'O', 'Ô': 'O', 'Ú': 'U', 'Ù': 'U', 'Û': 'U'}
            normalized = vowel_map.get(char_upper, char_upper)
            if is_word_start and i == 0 and normalized in 'AEIOU':
                variant_key = f"{normalized}a"
                if variant_key in special_tokens:
                    tokens.append({'token': char, 'img': special_tokens[variant_key]})
                    i += 1
                    continue
            img = letter_map.get(char_upper, fallback_image)
            tokens.append({'token': char, 'img': img})
            i += 1
    return tokens


def build_text_driven_sequence_enhanced(frame_states, text, project):  # noqa: C901 - (complex legacy logic retained)
    """Construct high‑fidelity frame sequence aligned to provided text.

    Includes anti‑truncation strategies, proportional duration preservation,
    smart token selection for compressed words, and final timing validation.
    """
    original_frame_count = len(frame_states) if frame_states else 0
    original_total_ms = sum(fs.get('ms', 0) for fs in (frame_states or []))
    if frame_states and len(frame_states) <= 10:
        corrected = frame_states
    else:
        print("🎬 APPLYING MANDATORY TIMING CORRECTION for lip sync consistency")
        corrected = validate_and_correct_frame_timing(frame_states)
    frame_states = corrected
    if original_frame_count and len(frame_states) != original_frame_count:
        print(f"🔧 Frame count changed during timing correction: {original_frame_count} → {len(frame_states)}")
    if not frame_states:
        print("🚨 DEBUG: frame_states is empty in build_text_driven_sequence_enhanced!")
        sequence = []
        letter_map = project.get('letter_map', {})
        fallback_image = project.get('fallback_image_abs') or project.get('fallback_image')
        for char in text:
            if char == ' ':
                sequence.append({'char': ' ', 'img': fallback_image, 'ms': 100, 'is_pause': True, 'source': 'text_fallback'})
            else:
                img = letter_map.get(char.upper(), fallback_image)
                sequence.append({'char': char, 'img': img or fallback_image, 'ms': 80, 'is_pause': False, 'source': 'text_fallback'})
        print(f"✅ Generated fallback sequence: {len(sequence)} frames from text")
        return sequence

    sequence = []
    letter_map = project.get('letter_map', {})
    special_tokens = project.get('special_tokens', {})
    fallback_image = project.get('fallback_image_abs') or project.get('fallback_image')
    pause_image = project.get('pause_image_abs') or project.get('pause_image')
    last_alignment = project.get('last_alignment')
    alignment_tokens = last_alignment.get('tokens') if last_alignment and 'tokens' in last_alignment else []

    # Build word boundaries & timestamps
    cumulative_time = 0.0
    frame_timestamps = []
    for state in frame_states:
        frame_timestamps.append(cumulative_time)
        cumulative_time += state.get('ms', 33.33) / 1000.0

    import re, unicodedata  # noqa: E401

    def normalize_for_comparison(s: str) -> str:
        s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
        return re.sub(r'[^a-zA-Z]', '', s).upper()

    text_words = re.findall(r'[a-zA-ZÀ-ÿ]+', text)
    text_words_normalized = [normalize_for_comparison(w) for w in text_words]
    word_boundaries = []
    current_word = ""
    current_word_start_frame = None
    current_word_start_time = None
    for i, state in enumerate(frame_states):
        active = state.get('active_word', '')
        ts = frame_timestamps[i]
        if active and not current_word:
            current_word, current_word_start_frame, current_word_start_time = active, i, ts
        elif current_word and (not active or active != current_word):
            if current_word_start_frame is not None:
                word_boundaries.append({'word': current_word, 'start': current_word_start_time, 'end': ts, 'start_frame': current_word_start_frame, 'end_frame': i - 1})
            if active:
                current_word, current_word_start_frame, current_word_start_time = active, i, ts
            else:
                current_word, current_word_start_frame, current_word_start_time = "", None, None
    if current_word and current_word_start_frame is not None:
        word_boundaries.append({'word': current_word, 'start': current_word_start_time, 'end': cumulative_time, 'start_frame': current_word_start_frame, 'end_frame': len(frame_states) - 1})

    print(f"📊 Found {len(word_boundaries)} word boundaries from frame states")
    word_to_tokens = {}
    used_indices = set()
    for i, boundary in enumerate(word_boundaries):
        boundary_norm = normalize_for_comparison(boundary['word'])
        if i < len(text_words_normalized) and i not in used_indices and text_words_normalized[i] == boundary_norm:
            tw = text_words[i]
            toks = tokenize_word_enhanced(tw, special_tokens, True, project)
            word_to_tokens[i] = {'tokens': toks, 'boundary': boundary, 'text_word': tw, 'boundary_index': i}
            used_indices.add(i)
            continue
        best = None
        for j, norm in enumerate(text_words_normalized):
            if j not in used_indices and norm == boundary_norm:
                best = j
                break
        if best is not None:
            tw = text_words[best]
            toks = tokenize_word_enhanced(tw, special_tokens, True, project)
            word_to_tokens[best] = {'tokens': toks, 'boundary': boundary, 'text_word': tw, 'boundary_index': i}
            used_indices.add(best)
    unmatched_text_indices = [i for i in range(len(text_words)) if i not in used_indices]
    unmatched_boundaries = [b for b in word_boundaries if not any(d['boundary'] == b for d in word_to_tokens.values())]
    for text_idx, boundary in zip(unmatched_text_indices, unmatched_boundaries):
        tw = text_words[text_idx]
        toks = tokenize_word_enhanced(tw, special_tokens, True, project)
        word_to_tokens[text_idx] = {'tokens': toks, 'boundary': boundary, 'text_word': tw, 'boundary_index': len(word_boundaries)}
    remaining = [i for i in range(len(text_words)) if i not in word_to_tokens]
    if remaining:
        print(f"🚨 EMERGENCY ANTI-TRUNCATION: Creating synthetic boundaries for {len(remaining)} words")
        last_end = word_boundaries[-1]['end_frame'] if word_boundaries else 0
        remaining_frames = len(frame_states) - last_end - 1
        frames_per = max(10, remaining_frames // len(remaining)) if remaining_frames > 0 else 10
        for idx, text_idx in enumerate(remaining):
            tw = text_words[text_idx]
            start_frame = last_end + 1 + (idx * frames_per)
            end_frame = min(len(frame_states) - 1, start_frame + frames_per - 1)
            synthetic = {'word': tw.upper(), 'start': start_frame / 30.0, 'end': end_frame / 30.0, 'start_frame': start_frame, 'end_frame': end_frame}
            toks = tokenize_word_enhanced(tw, special_tokens, True, project)
            word_to_tokens[text_idx] = {'tokens': toks, 'boundary': synthetic, 'text_word': tw, 'boundary_index': -1, 'synthetic': True}

    # Build sequence frame-by-frame
    last_was_pause = False
    for i, state in enumerate(frame_states):
        active_word = state.get('active_word', '')
        actual_ms = state.get('ms', 33.33)
        if not active_word or state.get('is_pause'):
            if not last_was_pause:
                sequence.append({'char': ' ', 'img': pause_image or fallback_image, 'fallback_img': fallback_image, 'ms': actual_ms, 'is_pause': True, 'source': 'frame_pause'})
                last_was_pause = True
            continue
        last_was_pause = False
        # Find boundary
        boundary_match = None
        for b in word_boundaries:
            if b['start_frame'] <= i <= b['end_frame']:
                boundary_match = b
                break
        if not boundary_match:
            for wd in word_to_tokens.values():
                if wd.get('synthetic'):
                    b = wd['boundary']
                    if b['start_frame'] <= i <= b['end_frame']:
                        boundary_match = b
                        break
        if boundary_match:
            matched_word = None
            for wd in word_to_tokens.values():
                if wd['boundary'] == boundary_match:
                    matched_word = wd
                    break
            if matched_word:
                tokens = matched_word['tokens']
                b = matched_word['boundary']
                frames_in_word = max(1, b['end_frame'] - b['start_frame'] + 1)
                frames_elapsed = i - b['start_frame']
                if len(tokens) == 1:
                    token_idx = 0
                elif frames_in_word >= len(tokens):
                    token_idx = min(int((frames_elapsed * (len(tokens) - 1)) / (frames_in_word - 1)), len(tokens) - 1)
                else:
                    if frames_in_word <= 1:
                        token_idx = 0
                    elif frames_in_word == 2:
                        token_idx = 0 if frames_elapsed == 0 else len(tokens) - 1
                    else:
                        progress = frames_elapsed / max(1, frames_in_word - 1)
                        token_idx = min(int(progress * (len(tokens) - 1)), len(tokens) - 1)
                token_data = tokens[token_idx]
                sequence.append({'char': token_data['token'], 'img': token_data.get('img') or fallback_image, 'fallback_img': fallback_image, 'ms': actual_ms, 'is_pause': False, 'word': matched_word['text_word'], 'token_idx': token_idx})
                continue
        # Fallback direct mapping
        char = active_word[0] if active_word else '?'
        sequence.append({'char': char, 'img': letter_map.get(char.upper(), fallback_image) or fallback_image, 'fallback_img': fallback_image, 'ms': actual_ms, 'is_pause': False})

    # Proportional duration preservation & validation (pared down from original)
    try:
        original_total_ms_precise = sum(fs.get('ms', 0) for fs in frame_states)
        sequence_total_ms = sum(f.get('ms', 0) for f in sequence)
        if sequence and original_total_ms_precise and abs(sequence_total_ms - original_total_ms_precise) > 50:
            scale = original_total_ms_precise / sequence_total_ms if sequence_total_ms > 0 else 1.0
            for f in sequence:
                f['ms'] = f.get('ms', 33.33) * scale
            adjusted_total = sum(f.get('ms', 0) for f in sequence)
            diff = original_total_ms_precise - adjusted_total
            if abs(diff) > 1 and sequence:
                sequence[-1]['ms'] += diff
            print(f"🔧 PROPORTIONAL SCALING APPLIED: scale={scale:.4f} diff corrected={diff:.2f}ms")
    except Exception as _e:  # noqa: BLE001
        print(f"⚠️  Duration scaling skipped due to error: {_e}")
    return sequence


@sequence_build_bp.route('/api/sequence/build-from-audio', methods=['POST'])
def build_sequence_from_audio():  # noqa: D401
    """Build sequence from audio alignment data (migrated from app.py)."""
    app_state = current_app.config['app_state']
    try:
        data = request.json or {}
        text = data.get('text', '')
        text_driven = data.get('text_driven', True)
        frame_states = []
        if data.get('frame_states'):
            frame_states = data['frame_states']
        if not frame_states and data.get('alignment_results'):
            alignment_data = data['alignment_results']
            frame_states = alignment_data.get('frame_states', [])
        if not frame_states:
            frame_states = (app_state['current_project'] or {}).get('frame_states', [])
        if not frame_states:
            last_alignment = (app_state['current_project'] or {}).get('last_alignment') or {}
            frame_states = last_alignment.get('frame_states', [])
        if not frame_states:
            existing_sequence = (app_state['current_project'] or {}).get('sequence', [])
            if existing_sequence:
                return jsonify({'success': True, 'sequence': existing_sequence, 'message': 'Using existing sequence (no frame states available)', 'stats': {'total_frames': len(existing_sequence)}})
            return jsonify({'success': False, 'error': 'No frame states or sequence data available. Please run audio alignment first.'}), 400
        print(f"🎬 Building sequence from {len(frame_states)} frame states (text-driven: {text_driven}, audio-timed)")
        if text_driven:
            sequence = build_text_driven_sequence_enhanced(frame_states, text, project=app_state['current_project'])
        else:
            # Legacy simplified path (kept minimal)
            sequence = []
            project = app_state['current_project'] or {}
            letter_map = project.get('letter_map', {})
            fallback_image = project.get('fallback_image_abs') or project.get('fallback_image')
            for state in frame_states:
                char = state.get('char') or state.get('viseme') or ''
                if not char:
                    continue
                sequence.append({'char': char[0].upper(), 'img': letter_map.get(char[0].upper(), fallback_image), 'ms': state.get('ms', 33.33), 'is_pause': False})
        app_state['current_project']['sequence'] = sequence  # persist
        return jsonify({'success': True, 'sequence': sequence, 'stats': {'total_frames': len(sequence)}})
    except Exception as e:  # noqa: BLE001
        return jsonify({'success': False, 'error': str(e)}), 500
