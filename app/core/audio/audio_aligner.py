# audio_aligner.py - Audio-driven animation timing for Face Sequencer Pro
"""
Audio alignment system for Portuguese-first lip-sync animation.
Derives precise word/phoneme timings from audio using forced alignment.
"""

from __future__ import annotations
import os
import librosa
import numpy as np
import json
import threading
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum

"""WP002 integration: centralized PyTorch compatibility via pytorch_compat.
The previous scattered monkey patches (torch_patch, inline torch.load overrides)
are being transitioned to an explicit safe_load wrapper to avoid hidden side-effects.
"""

try:  # Prefer new consolidated compatibility layer
    from app.core.utils.pytorch_compat import (
        safe_load,
        is_problematic_version,
        patched_load_context,
        ensure_whisperx_safe_globals,
    )
    # CRITICAL: Register safe globals IMMEDIATELY on module import to fix PyTorch 2.6+
    if is_problematic_version():
        ensure_whisperx_safe_globals()
        print("[PYTORCH] Safe globals registered on audio_aligner import (PyTorch 2.6+)")
except Exception as _import_err:  # pragma: no cover - fallback
    print(f"[WARNING] Failed to import pytorch_compat: {_import_err}")
    print("[WARNING] Applying inline PyTorch 2.6+ fix...")
    
    # Inline fix for PyTorch 2.6+ if import failed
    try:
        import torch
        if hasattr(torch, '__version__'):
            major, minor = map(int, torch.__version__.split(".")[:2])
            if (major > 2) or (major == 2 and minor >= 6):
                print("[PYTORCH] Detected PyTorch 2.6+, applying inline safe_globals fix")
                try:
                    import omegaconf
                    classes_to_register = []
                    for attr_name in ['ListConfig', 'DictConfig', 'OmegaConf']:
                        cls = getattr(omegaconf, attr_name, None)
                        if cls:
                            classes_to_register.append(cls)
                    if classes_to_register:
                        torch.serialization.add_safe_globals(classes_to_register)
                        print(f"[PYTORCH] Registered {len(classes_to_register)} OmegaConf classes inline")
                except Exception as e:
                    print(f"[WARNING] Inline safe_globals registration failed: {e}")
    except Exception as e:
        print(f"[WARNING] Inline PyTorch fix failed: {e}")
    
    # Fallback functions
    def safe_load(f, *a, **kw):  # type: ignore
        import torch
        return torch.load(f, *a, **kw)
    def is_problematic_version():  # type: ignore
        return False
    def patched_load_context():  # type: ignore
        import contextlib
        return contextlib.nullcontext()
    def ensure_whisperx_safe_globals():  # type: ignore
        pass

"""WP001: Dependency Injection refactor.

This module now relies on abstract Protocols defined in `audio_protocols.py`.
Concrete component instances can be injected directly or created via
`ComponentFactory` from `audio_factory.py`.
"""

# Import protocol interfaces (lightweight, no heavy model loads).
from app.core.audio.audio_protocols import (
    SilenceDetectorProtocol,
    ForcedAlignerProtocol,
    FrameSynchronizerProtocol,
)

try:  # Optional factory (may not be needed in tests)
    from app.core.audio.audio_factory import ComponentFactory
except ImportError:  # Fallback if factory not present
    class ComponentFactory:  # type: ignore
        """Stub ComponentFactory used when real factory not available."""
        def __init__(self, *_, **__):
            raise RuntimeError("ComponentFactory not available; install full audio stack")

# Type checking only imports for rich types (not required at runtime)
from typing import TYPE_CHECKING
if TYPE_CHECKING:  # pragma: no cover
    from app.core.export.frame_synchronizer import WordTiming, FrameState
    from app.core.audio.forced_alignment import AlignmentResult as ForcedAlignmentInternal

class TokenType(Enum):
    WORD = "word"
    PHONEME = "phoneme" 
    GAP = "gap"

@dataclass
class AlignmentToken:
    """Individual aligned token (word/phoneme/gap) with timing"""
    type: TokenType
    text: str
    viseme: Optional[str]
    start_ms: float
    end_ms: float
    confidence: float
    lang: str
    
# NOTE: We intentionally DO NOT patch torch.load globally here anymore.
# Call sites should use pytorch_compat.safe_load when loading model weights.
# This keeps side-effects explicit and localized.

@dataclass 
class AlignmentStats:
    """Quality metrics for alignment result"""
    audio_ms: float
    drift_ms: float
    unaligned_count: int
    avg_confidence: float
    pause_count: int

@dataclass
class AlignmentResult:
    """Complete alignment result with tokens and quality stats"""
    language: str
    sample_rate: int
    tokens: List[AlignmentToken]
    stats: AlignmentStats

class AudioAligner:
    """
    Main audio alignment class supporting pt-BR and en-US.
    Uses WhisperX for forced alignment and WebRTC VAD for gap detection.
    
    Implements dependency injection pattern to avoid circular imports.
    """
    
    def __init__(
        self,
        language: str = "pt-BR",
        device: str = "auto",
        silence_detector: Optional[SilenceDetectorProtocol] = None,
        forced_aligner: Optional[ForcedAlignerProtocol] = None,
        aligner: Optional[ForcedAlignerProtocol] = None,  # backward-compatible alias
        frame_synchronizer: Optional[FrameSynchronizerProtocol] = None,
        factory: Optional[ComponentFactory] = None,
        auto_build_enhanced: bool = True,
    ):
        # Configure logger
        from app.core.utils.logger import get_logger
        self.logger = get_logger(__name__)
        """Create an AudioAligner.

        Args:
            language: Language code (e.g. pt-BR, en-US)
            device: Compute device or 'auto'
            silence_detector: Injected silence detector (Protocol)
            forced_aligner: Injected forced aligner (Protocol)
            frame_synchronizer: Injected frame synchronizer (Protocol)
            factory: Optional ComponentFactory to lazily build components
            auto_build_enhanced: If True and components missing, attempt to build via factory
        """
        self.language = language
        self.device = self._setup_device(device)
        self.models: Dict[str, Any] = {}

        self._factory = factory
        # Prefer explicitly passed components; only use factory if missing
        self.silence_detector = silence_detector
        # Support legacy 'aligner' parameter name
        self.forced_aligner = forced_aligner or aligner
        self.frame_synchronizer = frame_synchronizer

        if auto_build_enhanced and self._factory and (
            self.silence_detector is None
            or self.forced_aligner is None
            or self.frame_synchronizer is None
        ):
            try:
                sd, fa, fs = self._factory.build_enhanced_stack()  # type: ignore[attr-defined]
                self.silence_detector = self.silence_detector or sd
                self.forced_aligner = self.forced_aligner or fa
                self.frame_synchronizer = self.frame_synchronizer or fs
                print("[CHECK] Enhanced components built via factory")
            except Exception as e:  # pragma: no cover - defensive
                print(f"[WARNING] Failed to build enhanced stack: {e}")

        # Determine enhanced availability
        self.use_enhanced = all([
            isinstance(self.silence_detector, SilenceDetectorProtocol),
            isinstance(self.forced_aligner, ForcedAlignerProtocol),
            isinstance(self.frame_synchronizer, FrameSynchronizerProtocol),
        ])

        if self.use_enhanced:
            self.logger.info("[ROCKET] Using enhanced alignment pipeline (DI)")
        else:
            self.logger.info("[NOTE] Falling back to legacy WhisperX-based alignment pipeline")

        # Portuguese-specific configuration
        self.pt_br_config = {
            "contractions": {
                "do": "de o", "da": "de a", "na": "em a", "no": "em o",
                "num": "em um", "numa": "em uma", "pelo": "por o",
                "pela": "por a", "deste": "de este", "desta": "de esta"
            },
            "phoneme_to_viseme": {
                # Nasal vowels - key characteristic of Portuguese
                "ã": "nasal_a", "õ": "nasal_o", "ẽ": "nasal_e",
                # Consonants
                "p": "P", "b": "B", "t": "T", "d": "D", "k": "K", "g": "G",
                "f": "F", "v": "V", "s": "S", "z": "Z", 
                "ʃ": "SH", "ʒ": "ZH", "h": "H",
                "m": "M", "n": "N", "ɲ": "NH",
                "l": "L", "ʎ": "LH", "ɾ": "R_tap", "ʁ": "R_fricative",
                # Vowels
                "a": "A", "e": "E", "i": "I", "o": "O", "u": "U"
            }
        }
        
        # Legacy path uses WhisperX if enhanced components unavailable
        
    def _setup_device(self, device: str) -> str:
        """Determine optimal device for processing"""
        if device == "auto":
            try:
                import torch
                return "cuda" if torch.cuda.is_available() else "cpu"
            except ImportError:
                return "cpu"
        return device
    
    def preprocess_audio(self, audio_path: str) -> Tuple[np.ndarray, int]:
        """
        Load and preprocess audio for alignment
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Tuple of (audio_array, sample_rate)
        """
        # Load audio with sample rate from config
        from app.core.utils.config import config
        print(f"🔊 Loading and preprocessing audio: {os.path.basename(audio_path)}")

        target_sr = config.audio.sample_rate()
        # Lightweight in-process cache to avoid re-decoding identical files during a single request burst
        if not hasattr(self, "_preproc_cache"):
            self._preproc_cache = {}
        cache_key = (audio_path, target_sr, os.path.getmtime(audio_path))
        cached = self._preproc_cache.get(cache_key)
        if cached:
            return cached
        ext = os.path.splitext(audio_path)[1].lower()
        audio = None
        sr = target_sr

        def _read_wav_basic(path: str, sr_target: int) -> Tuple[np.ndarray, int]:
            """Lightweight WAV reader using soundfile or wave to avoid librosa/numba when broken."""
            try:
                import soundfile as sf  # type: ignore
                data, sr_local = sf.read(path, always_2d=False)
                if data.ndim > 1:
                    data = np.mean(data, axis=1)
                if sr_local != sr_target:
                    # Simple resample via numpy (linear) if no librosa
                    ratio = sr_target / sr_local
                    idxs = np.arange(0, len(data) * ratio, ratio)
                    idxs = idxs[idxs < len(data)]
                    data = np.interp(idxs, np.arange(len(data)), data)
                    sr_local = sr_target
                return data.astype(np.float32), sr_local
            except Exception:
                import wave, contextlib
                with contextlib.closing(wave.open(path, 'rb')) as wf:
                    sr_local = wf.getframerate()
                    n = wf.getnframes()
                    raw = wf.readframes(n)
                audio_np = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
                if sr_local != sr_target:
                    ratio = sr_target / sr_local
                    idxs = np.arange(0, len(audio_np) * ratio, ratio)
                    idxs = idxs[idxs < len(audio_np)]
                    audio_np = np.interp(idxs, np.arange(len(audio_np)), audio_np)
                    sr_local = sr_target
                return audio_np, sr_local

        def _ffmpeg_decode(tmp_path: str) -> Tuple[np.ndarray, int]:
            """Decode via ffmpeg to wav (mono) as a robust fallback for webm/opus or exotic containers.
            Avoids librosa to prevent llvmlite dependency when environment lacks LLVM libs."""
            import subprocess, uuid, tempfile
            wav_path = os.path.join(tempfile.gettempdir(), f"_fs_tmp_{uuid.uuid4().hex}.wav")
            cmd = [
                'ffmpeg','-y','-i', tmp_path,
                '-ac','1','-ar', str(target_sr), '-vn', wav_path
            ]
            try:
                subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=25, check=True)
                data, wsr = _read_wav_basic(wav_path, target_sr)
                return data, wsr
            except Exception as fe:
                print(f"[WARNING] FFmpeg fallback failed: {fe}")
                raise
            finally:
                try:
                    if os.path.exists(wav_path):
                        os.remove(wav_path)
                except Exception:
                    pass

        tried_ffmpeg = False
        # Suppress verbose PySoundFile/audioread warnings that spam logs when trying exotic containers
        import warnings as _warnings
        with _warnings.catch_warnings():
            _warnings.filterwarnings("ignore", category=UserWarning, module="soundfile")
            use_librosa = os.environ.get("FS_DISABLE_LIBROSA", "0").lower() not in {"1", "true", "yes"}
            if use_librosa:
                try:
                    # Direct load first (librosa)
                    import librosa  # local import so failure is caught
                    audio, sr = librosa.load(audio_path, sr=target_sr, mono=True)
                except Exception as e:
                    print(f"[WARNING] Direct decode (librosa) failed ({e}); attempting ffmpeg fallback")
                    try:
                        audio, sr = _ffmpeg_decode(audio_path)
                        tried_ffmpeg = True
                    except Exception:
                        # Last chance: try raw WAV read if file already WAV
                        ext_l = os.path.splitext(audio_path)[1].lower()
                        if ext_l == '.wav':
                            try:
                                audio, sr = _read_wav_basic(audio_path, target_sr)
                            except Exception:
                                raise
                        else:
                            raise
            else:
                try:
                    audio, sr = _ffmpeg_decode(audio_path)
                    tried_ffmpeg = True
                except Exception:
                    ext_l = os.path.splitext(audio_path)[1].lower()
                    if ext_l == '.wav':
                        audio, sr = _read_wav_basic(audio_path, target_sr)
                    else:
                        raise

        if audio is not None:
            rms_initial = float(np.sqrt(np.mean(audio**2))) if audio.size else 0.0
            if (rms_initial < 1e-6) and (ext in {'.webm', '.mkv', '.ogg'}) and not tried_ffmpeg:
                # Silent or zeroed decode; retry via ffmpeg
                print("[WARNING] Very low RMS after direct load; retrying decode via ffmpeg for container-based audio")
                try:
                    audio, sr = _ffmpeg_decode(audio_path)
                    tried_ffmpeg = True
                except Exception:
                    print("[WARNING] FFmpeg retry also failed; proceeding with low-amplitude audio")
        
        # Check audio levels
        rms = np.sqrt(np.mean(audio**2)) if audio is not None and audio.size else 0.0
        print(f"[CHART] Audio RMS level before processing: {rms:.4f}")
        
        # Strong normalization for low-level audio
        try:
            import librosa
            audio = librosa.util.normalize(audio) * config.audio.normalize_level()
        except Exception:
            # Simple manual normalization
            peak = np.max(np.abs(audio)) if audio.size else 1.0
            if peak > 0:
                audio = (audio / peak) * config.audio.normalize_level()
        
        # Enhanced denoising - reduce background noise
        try:
            import librosa
            audio = librosa.effects.preemphasis(audio, coef=config.audio.preemphasis_coef())
        except Exception:
            # Basic high-pass style emphasis (difference filter)
            coef = config.audio.preemphasis_coef()
            if audio.size > 1:
                audio = np.append(audio[0], audio[1:] - coef * audio[:-1])
        
        # Apply gentle high-pass filter to remove rumble (for all audio types)
        from scipy.signal import butter, filtfilt
        nyq = 0.5 * sr
        cutoff = config.audio.high_pass_cutoff() / nyq  # High-pass filter from config
        b, a = butter(3, cutoff, btype='high')
        audio = filtfilt(b, a, audio)
        
        # Apply light trimming for all audio sources
        try:
            import librosa
            audio, _ = librosa.effects.trim(audio, top_db=config.audio.trim_top_db())  # Trimming level from config
        except Exception as tr_e:
            print(f"[WARNING] Trim step failed (librosa unavailable?): {tr_e}")
        
        # Final check of audio levels after processing
        rms_after = np.sqrt(np.mean(audio**2))
        print(f"[CHART] Audio RMS level after processing: {rms_after:.4f}")
        
        # Ensure array is contiguous to avoid negative stride issues with PyTorch
        if not audio.flags['C_CONTIGUOUS']:
            print("[FIX] Creating contiguous audio array...")
            audio = np.ascontiguousarray(audio)

        # Store in lightweight cache (in-process only)
        self._preproc_cache[cache_key] = (audio, sr)
        return audio, sr
    
    def preprocess_text(self, text: str) -> str:
        """
        Normalize text for alignment, handling Portuguese specifics
        
        Args:
            text: Input transcript
            
        Returns:
            Normalized text ready for alignment
        """
        import re
        
        # Preserve Portuguese diacritics
        text = text.strip()
        
        if self.language == "pt-BR":
            # Expand common Portuguese contractions
            for contraction, expansion in self.pt_br_config["contractions"].items():
                # Word boundary aware replacement
                pattern = r'\b' + re.escape(contraction) + r'\b'
                text = re.sub(pattern, expansion, text, flags=re.IGNORECASE)
        
        # Normalize punctuation but preserve meaning
        text = re.sub(r'[""]', '"', text)  # Standardize quotes  
        text = re.sub(r"['']", "'", text)  # Standardize apostrophes
        text = re.sub(r'—', '-', text)      # Em dash to hyphen

        # Map symbols to spoken forms for Portuguese to improve alignment
        # Example: transcript uses '/', but audio says 'barra'
        if self.language.startswith("pt"):
            # Protect URLs to avoid mangling slashes in http:// or paths
            url_placeholders = {}

            def _protect_url(m):
                key = f"__URL{len(url_placeholders)}__"
                url_placeholders[key] = m.group(0)
                return key

            # Basic URL patterns (http(s) and www)
            text = re.sub(r'https?://\S+|www\.\S+', _protect_url, text)

            # Replace standalone or between-words slashes with ' barra '
            # Case 1: surrounded by optional spaces between word chars
            text = re.sub(r'(?<=\w)\s*/\s*(?=\w)', ' barra ', text)
            # Case 2: explicit spaces around slash
            text = re.sub(r'\s+/\s+', ' barra ', text)

            # Replace percent after digits with 'por cento'
            text = re.sub(r'(\d)\s*%', r'\1 por cento', text)

            # Safe replacements for a few common symbols when separated by spaces
            text = re.sub(r'\s*&\s*', ' e ', text)            # & -> e
            text = re.sub(r'\s*#\s*', ' hashtag ', text)      # # -> hashtag
            text = re.sub(r'\s*@\s*', ' arroba ', text)       # @ -> arroba
            text = re.sub(r'\s*_\s*', ' underline ', text)    # _ -> underline

            # Restore protected URLs
            for k, v in url_placeholders.items():
                text = text.replace(k, v)

        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def align_with_whisperx(self, audio: np.ndarray, transcript: str) -> Dict:
        """
        Perform forced alignment using WhisperX
        
        Args:
            audio: Preprocessed audio array
            transcript: Normalized transcript
            
        Returns:
            WhisperX alignment result
        """
        # Import WhisperX (safe globals already registered on module load)
        try:
            import whisperx  # type: ignore
        except ImportError:
            raise ImportError("whisperx not installed. Run: pip install whisperx")
        
        # Load models if not cached
        if 'transcribe' not in self.models:
            # Use the tiny model for faster processing and lower memory usage
            print("[REFRESH] Loading WhisperX transcription model (first run may take longer)...")
            # Wrap in context to enforce safe torch.load behavior inside library
            if is_problematic_version():
                with patched_load_context():
                    self.models['transcribe'] = whisperx.load_model(
                        "tiny", self.device, compute_type="int8"
                    )
            else:
                self.models['transcribe'] = whisperx.load_model(
                    "tiny", self.device, compute_type="int8"
                )
            print("[CHECK] WhisperX transcription model loaded")
        
        if 'align' not in self.models:
            print(f"[REFRESH] Loading alignment model for language {self.language[:2]}...")
            try:
                if is_problematic_version():
                    with patched_load_context():
                        self.models['align'], self.models['align_meta'] = whisperx.load_align_model(
                            language_code=self.language[:2], device=self.device  # pt-BR -> pt
                        )
                else:
                    self.models['align'], self.models['align_meta'] = whisperx.load_align_model(
                        language_code=self.language[:2], device=self.device  # pt-BR -> pt
                    )
                print("[CHECK] Alignment model loaded")
            except Exception as e:
                print(f"[WARNING] Error loading alignment model: {e}")
                print(f"[REFRESH] Falling back to word-level alignment only")
                # Set dummy alignment model and metadata
                self.models['align'] = None
                self.models['align_meta'] = None
        
        # Initial transcription with word timestamps
        # Fix negative stride issue by ensuring audio is contiguous
        if not audio.flags['C_CONTIGUOUS']:
            print("[FIX] Audio array has negative strides, creating contiguous copy...")
            audio = np.ascontiguousarray(audio)
        
        result = self.models['transcribe'].transcribe(
            audio, 
            batch_size=16,
            language=self.language[:2]
        )
        
        # Forced alignment for precise boundaries
        if self.models['align'] is not None:
            try:
                aligned_result = whisperx.align(
                    result["segments"], 
                    self.models['align'], 
                    self.models['align_meta'], 
                    audio, 
                    self.device,
                    return_char_alignments=False
                )
            except Exception as e:
                print(f"[WARNING] Error during alignment: {e}")
                print(f"[REFRESH] Using only word-level timing from transcription")
                # Just use the original transcription result if alignment fails
                aligned_result = result
        else:
            # If alignment model couldn't be loaded, just use the transcription result
            print(f"[REFRESH] Using only word-level timing from transcription (no alignment model)")
            aligned_result = result
        
        return aligned_result
    
    def detect_gaps_with_vad(self, audio: np.ndarray, sample_rate: int, 
                           frame_duration_ms: int = 30) -> List[Tuple[float, float]]:
        """
        Detect speech gaps using Voice Activity Detection
        
        Args:
            audio: Audio array
            sample_rate: Audio sample rate
            frame_duration_ms: VAD frame duration in milliseconds
            
        Returns:
            List of (start_ms, end_ms) tuples for gaps
        """
        try:
            import webrtcvad
        except ImportError:
            # Fallback to energy-based detection
            return self._detect_gaps_energy_based(audio, sample_rate)
        
        vad = webrtcvad.Vad(2)  # Aggressiveness level 2 (0-3)
        frame_duration = frame_duration_ms / 1000.0  # Convert to seconds
        frame_length = int(frame_duration * sample_rate)
        
        gaps = []
        current_gap_start = None
        
        for i in range(0, len(audio), frame_length):
            frame = audio[i:i + frame_length]
            
            # Pad short frames
            if len(frame) < frame_length:
                frame = np.pad(frame, (0, frame_length - len(frame)))
            
            # Convert to bytes for webrtcvad
            frame_bytes = (frame * 32767).astype(np.int16).tobytes()
            
            try:
                is_speech = vad.is_speech(frame_bytes, sample_rate)
            except:
                is_speech = True  # Assume speech on VAD errors
            
            time_ms = i / sample_rate * 1000
            
            if not is_speech:
                if current_gap_start is None:
                    current_gap_start = time_ms
            else:
                if current_gap_start is not None:
                    gap_duration = time_ms - current_gap_start
                    if gap_duration >= 300:  # Minimum gap duration (increased to 300ms for better phrase grouping)
                        gaps.append((current_gap_start, time_ms))
                    current_gap_start = None
        
        # Handle gap at end of audio
        if current_gap_start is not None:
            gaps.append((current_gap_start, len(audio) / sample_rate * 1000))
        
        return gaps
    
    def _detect_gaps_energy_based(self, audio: np.ndarray, sample_rate: int) -> List[Tuple[float, float]]:
        """Fallback gap detection using audio energy"""
        # Simple energy-based gap detection
        hop_length = 512
        frame_length = 2048
        
        # Calculate RMS energy
        rms = librosa.feature.rms(
            y=audio, 
            frame_length=frame_length, 
            hop_length=hop_length
        )[0]
        
        # Convert frames to time
        times = librosa.frames_to_time(
            np.arange(len(rms)), 
            sr=sample_rate, 
            hop_length=hop_length
        )
        
        # Simple threshold-based gap detection
        threshold = np.mean(rms) * 0.1  # 10% of mean energy
        is_silent = rms < threshold
        
        gaps = []
        gap_start = None
        
        for i, (time, silent) in enumerate(zip(times, is_silent)):
            if silent and gap_start is None:
                gap_start = time * 1000  # Convert to ms
            elif not silent and gap_start is not None:
                gap_duration = time * 1000 - gap_start
                if gap_duration >= 300:  # Minimum gap duration (increased to 300ms for better phrase grouping)
                    gaps.append((gap_start, time * 1000))
                gap_start = None
        
        return gaps
    
    def merge_tokens_and_gaps(self, alignment_result: Dict, gaps: List[Tuple[float, float]], normalized_text: str) -> List[AlignmentToken]:
        """
        Merge aligned words with detected gaps into unified token stream and reconcile
        with the expected transcript to avoid drift when symbols/words don't match.
        
        STRATEGY: Use WhisperX tokens as ANCHOR POINTS only, then redistribute expected
        transcript words proportionally across the actual audio duration between anchors.
        This prevents compression/drift when model misses or merges words.
        
        Args:
            alignment_result: WhisperX alignment result (used as anchors)
            gaps: List of gap intervals from VAD
            normalized_text: Preprocessed transcript used for alignment
            
        Returns:
            List of AlignmentTokens including words and gaps
        """
        import re
        
        # Extract expected words from transcript
        expected_words = [w for w in re.findall(r"\w+", normalized_text, flags=re.UNICODE) if w.strip()]
        
        if not expected_words:
            # No expected words, return empty
            return []
        
        # Extract observed tokens from WhisperX as anchor points
        observed_tokens: List[AlignmentToken] = []
        for segment in alignment_result.get("segments", []):
            for word_info in segment.get("words", []):
                token = AlignmentToken(
                    type=TokenType.WORD,
                    text=word_info["word"].strip(),
                    viseme=self._text_to_viseme(word_info["word"].strip()),
                    start_ms=word_info["start"] * 1000,
                    end_ms=word_info["end"] * 1000,
                    confidence=word_info.get("score", 0.5),
                    lang=self.language
                )
                observed_tokens.append(token)
        
        print(f"[ANCHOR] WhisperX gave {len(observed_tokens)} tokens for {len(expected_words)} expected words")
        
        # Build phrase windows from VAD gaps
        phrase_windows: List[Tuple[float, float]] = []
        sorted_gaps = sorted(gaps, key=lambda x: x[0])
        prev_end = 0.0
        for (gap_start, gap_end) in sorted_gaps:
            if gap_start > prev_end:
                phrase_windows.append((prev_end, gap_start))
            prev_end = gap_end
        
        # Final window from last gap to end of last observed token (or add buffer)
        if observed_tokens:
            final_end = max(observed_tokens[-1].end_ms, prev_end)
            if final_end > prev_end:
                phrase_windows.append((prev_end, final_end))
        elif expected_words:
            # No observed tokens at all - use full duration estimate
            phrase_windows.append((0.0, len(expected_words) * 200))  # 200ms per word estimate
        
        print(f"[WINDOW] Built {len(phrase_windows)} phrase windows from {len(gaps)} gaps")
        
        # Distribute expected words across phrase windows proportionally
        reconciled_tokens: List[AlignmentToken] = []
        word_idx = 0
        
        for window_idx, (window_start, window_end) in enumerate(phrase_windows):
            window_duration = window_end - window_start
            
            # Find observed tokens in this window as anchors
            window_observed = [t for t in observed_tokens 
                             if t.start_ms >= window_start and t.end_ms <= window_end]
            
            # Estimate how many expected words belong to this window
            # Use ratio of observed tokens if available, otherwise split evenly
            if window_observed and observed_tokens:
                words_in_window = max(1, int(len(expected_words) * len(window_observed) / len(observed_tokens)))
            else:
                remaining_words = len(expected_words) - word_idx
                remaining_windows = len(phrase_windows) - window_idx
                words_in_window = max(1, remaining_words // max(1, remaining_windows))
            
            # Don't exceed remaining words
            words_in_window = min(words_in_window, len(expected_words) - word_idx)
            
            if words_in_window == 0:
                continue
            
            # Distribute these words evenly across the window duration
            word_duration = window_duration / words_in_window
            
            for i in range(words_in_window):
                if word_idx >= len(expected_words):
                    break
                
                word_start = window_start + (i * word_duration)
                word_end = window_start + ((i + 1) * word_duration)
                
                # Use confidence from nearby observed token if available
                conf = 0.7
                if window_observed:
                    # Find closest observed token
                    closest = min(window_observed, key=lambda t: abs(t.start_ms - word_start))
                    conf = closest.confidence
                
                token = AlignmentToken(
                    type=TokenType.WORD,
                    text=expected_words[word_idx],
                    viseme=self._text_to_viseme(expected_words[word_idx]),
                    start_ms=word_start,
                    end_ms=word_end,
                    confidence=conf,
                    lang=self.language
                )
                reconciled_tokens.append(token)
                word_idx += 1
        
        # Handle any remaining expected words (distribute after last window)
        if word_idx < len(expected_words):
            print(f"[FALLBACK] {len(expected_words) - word_idx} words remain, appending...")
            last_end = reconciled_tokens[-1].end_ms if reconciled_tokens else 0.0
            for i in range(word_idx, len(expected_words)):
                start_ms = last_end + (i - word_idx) * 150
                end_ms = start_ms + 150
                token = AlignmentToken(
                    type=TokenType.WORD,
                    text=expected_words[i],
                    viseme=self._text_to_viseme(expected_words[i]),
                    start_ms=start_ms,
                    end_ms=end_ms,
                    confidence=0.5,
                    lang=self.language
                )
                reconciled_tokens.append(token)
        
        print(f"[RECONCILE] Generated {len(reconciled_tokens)} tokens from {len(expected_words)} expected words")
        
        # Now insert GAP tokens
        all_tokens: List[AlignmentToken] = []
        for gap_start, gap_end in gaps:
            gap_token = AlignmentToken(
                type=TokenType.GAP,
                text="",
                viseme="neutral",
                start_ms=gap_start,
                end_ms=gap_end,
                confidence=1.0,
                lang=self.language
            )
            all_tokens.append(gap_token)
        
        # Merge and sort by start time
        all_tokens.extend(reconciled_tokens)
        all_tokens.sort(key=lambda t: t.start_ms)
        
        return all_tokens

    def _reconcile_with_transcript(self, observed_tokens: List[AlignmentToken], text: str, gaps: List[Tuple[float, float]] | None = None) -> List[AlignmentToken]:
        """Align expected transcript to observed tokens em batches (5 em 5) para reduzir drift global.
        Para cada batch de 5 palavras do transcript, procura a melhor janela contígua nos tokens observados
        (busca local) e distribui as palavras esperadas nesse intervalo, cortando no próximo silêncio se existir.
        """
        import re, difflib

        # Extrai palavras do transcript (ignora pontuação pura)
        exp_words = [w for w in re.findall(r"\w+", text, flags=re.UNICODE) if w.strip()]
        if not exp_words:
            return observed_tokens
        obs_word_tokens = [t for t in observed_tokens if t.type == TokenType.WORD]
        if not obs_word_tokens:
            return observed_tokens

        obs_low = [t.text.lower() for t in obs_word_tokens]

        def next_silence_after(ms: float) -> float | None:
            if not gaps:
                return None
            for (gs, ge) in sorted(gaps, key=lambda x: x[0]):
                if ge > ms:
                    return gs
            return None

        def make_token(txt: str, s: float, e: float, conf: float) -> AlignmentToken:
            return AlignmentToken(
                type=TokenType.WORD,
                text=txt,
                viseme=self._text_to_viseme(txt),
                start_ms=s,
                end_ms=e,
                confidence=conf,
                lang=self.language,
            )

        B = 5
        reconciled: List[AlignmentToken] = []
        i = 0
        j = 0  # ponteiro nos tokens observados
        prev_end = 0.0
        if obs_word_tokens:
            prev_end = max(0.0, obs_word_tokens[0].start_ms)

        while i < len(exp_words):
            batch = exp_words[i:i+B]
            batch_low = [w.lower() for w in batch]
            best = None  # (ratio, s, e)
            max_start = min(j + 15, len(obs_word_tokens))
            for s in range(j, max_start):
                for e in range(s, min(s + B + 5, len(obs_word_tokens))):
                    cand = obs_low[s:e+1]
                    ratio = difflib.SequenceMatcher(a=batch_low, b=cand, autojunk=False).ratio()
                    if best is None or ratio > best[0]:
                        best = (ratio, s, e)

            if best and best[0] >= 0.3:
                _, s, e = best
                span_start = obs_word_tokens[s].start_ms
                span_end = obs_word_tokens[e].end_ms
                ns = next_silence_after(span_start)
                if ns is not None:
                    span_end = min(span_end, ns)
                # segurança
                if span_end <= span_start:
                    span_end = span_start + 60 * len(batch)
                conf = min(obs_word_tokens[k].confidence for k in range(s, e+1)) if e >= s else 0.5
                n = len(batch)
                step = (span_end - span_start) / max(n, 1)
                for idx in range(n):
                    s_ms = span_start + step * idx
                    e_ms = span_start + step * (idx + 1)
                    reconciled.append(make_token(batch[idx], s_ms, e_ms, conf))
                j = e + 1
                prev_end = span_end
            else:
                # Sem janela observada boa: coloque entre prev_end e próximo observado ou próxima pausa
                next_obs_start = obs_word_tokens[j].start_ms if j < len(obs_word_tokens) else None
                ns = next_silence_after(prev_end)
                end_bound = None
                if next_obs_start is not None and ns is not None:
                    end_bound = min(next_obs_start, ns)
                elif next_obs_start is not None:
                    end_bound = next_obs_start
                elif ns is not None:
                    end_bound = ns
                n = len(batch)
                if end_bound is not None and end_bound > prev_end:
                    step = (end_bound - prev_end) / n
                    for idx in range(n):
                        s_ms = prev_end + step * idx
                        e_ms = prev_end + step * (idx + 1)
                        reconciled.append(make_token(batch[idx], s_ms, e_ms, 0.3))
                    prev_end = end_bound
                else:
                    # fallback: 120ms por palavra sequencialmente
                    for idx in range(n):
                        s_ms = prev_end + 120 * idx
                        e_ms = s_ms + 120
                        reconciled.append(make_token(batch[idx], s_ms, e_ms, 0.3))
                    prev_end = reconciled[-1].end_ms
            i += B

        # Ordena e corrige monotonicidade
        reconciled.sort(key=lambda t: t.start_ms)
        last_end = None
        for t in reconciled:
            if last_end is not None and t.start_ms < last_end:
                t.start_ms = last_end
                if t.end_ms < t.start_ms:
                    t.end_ms = t.start_ms + 40
            last_end = t.end_ms

        # Estica dentro de janelas de frase (entre silêncios) se sobrar muito espaço
        try:
            if gaps:
                windows: List[Tuple[float, float]] = []
                start0 = 0.0
                for (gs, ge) in sorted(gaps, key=lambda x: x[0]):
                    if gs > start0:
                        windows.append((start0, gs))
                    start0 = ge
                if reconciled:
                    windows.append((start0, reconciled[-1].end_ms))
                for w_start, w_end in windows:
                    bucket = [tok for tok in reconciled if not (tok.end_ms <= w_start or tok.start_ms >= w_end)]
                    if len(bucket) < 2:
                        continue
                    cur_start = min(t.start_ms for t in bucket)
                    cur_end = max(t.end_ms for t in bucket)
                    room = w_end - cur_end
                    if room >= 400:
                        span = max(cur_end - cur_start, 1.0)
                        scale = (w_end - cur_start) / span
                        for tok in bucket:
                            tok.start_ms = w_start + (tok.start_ms - cur_start) * scale
                            tok.end_ms = w_start + (tok.end_ms - cur_start) * scale
                # Reforça monotonicidade
                reconciled.sort(key=lambda t: t.start_ms)
                le = None
                for t in reconciled:
                    if le is not None and t.start_ms < le:
                        t.start_ms = le
                        if t.end_ms < t.start_ms:
                            t.end_ms = t.start_ms + 40
                    le = t.end_ms
        except Exception as _e:
            print(f"[WARNING] Batch phrase stretching skipped: {_e}")

        return reconciled
    
    def generate_text_based_tokens(self, text: str, audio_duration_ms: float, language: str, audio: np.ndarray = None, sample_rate: int = None) -> List[AlignmentToken]:
        """
        Generate alignment tokens based solely on the text and audio duration.
        This is a fallback method when forced alignment fails.
        NOW WITH VAD: Uses Voice Activity Detection to create realistic phrase windows!
        
        Args:
            text: Text to convert to tokens
            audio_duration_ms: Total audio duration in milliseconds
            language: Language code
            audio: Optional audio array for VAD-based segmentation
            sample_rate: Sample rate of audio
            
        Returns:
            List of AlignmentToken objects
        """
        print(f"[FALLBACK-VAD] Generating VAD-based tokens for {len(text)} characters over {audio_duration_ms:.2f}ms")
        print(f"[FALLBACK-VAD] CODE VERSION: 2025-01-06-v3 (with word count tracking)")
        
        # Extract words from text
        import re
        expected_words = [w for w in re.findall(r"\w+", text, flags=re.UNICODE) if w.strip()]
        print(f"[FALLBACK-VAD] Extracted {len(expected_words)} words from normalized text")
        print(f"[FALLBACK-VAD] First 10 words: {' '.join(expected_words[:10])}")
        
        # If no words, return single token for the whole duration
        if not expected_words:
            return [AlignmentToken(
                type=TokenType.WORD,
                text=text or "silence",
                viseme=self._text_to_viseme(text or "A"),
                start_ms=0,
                end_ms=audio_duration_ms,
                confidence=0.5,
                lang=language
            )]
        
        # Try VAD-based distribution if audio is available
        if audio is not None and sample_rate is not None:
            try:
                print(f"[FALLBACK-VAD] Using VAD to detect phrase boundaries...")
                gaps = self.detect_gaps_with_vad(audio, sample_rate)
                print(f"[FALLBACK-VAD] Detected {len(gaps)} pauses")
                
                # Build phrase windows from VAD gaps (same strategy as merge_tokens_and_gaps)
                phrase_windows: List[Tuple[float, float]] = []
                sorted_gaps = sorted(gaps, key=lambda x: x[0])
                prev_end = 0.0
                for (gap_start, gap_end) in sorted_gaps:
                    if gap_start > prev_end:
                        phrase_windows.append((prev_end, gap_start))
                    prev_end = gap_end
                
                # Final window
                if prev_end < audio_duration_ms:
                    phrase_windows.append((prev_end, audio_duration_ms))
                elif not phrase_windows:
                    phrase_windows.append((0.0, audio_duration_ms))
                
                print(f"[FALLBACK-VAD] Created {len(phrase_windows)} phrase windows")
                print(f"[FALLBACK-VAD] Total words to distribute: {len(expected_words)}")
                
                # IMPROVED APPROACH: Detect onset peaks within each window for word boundaries
                tokens = []
                word_idx = 0
                total_words = len(expected_words)
                
                # Calculate total speech duration
                total_speech_duration = sum(end - start for start, end in phrase_windows)
                print(f"[FALLBACK-VAD] Total speech duration: {total_speech_duration:.0f}ms")
                print(f"[FALLBACK-VAD] Average speech rate: {(total_words / (total_speech_duration/1000.0)):.2f} words/sec")
                
                # Detect onset peaks (word boundaries) within each window
                print(f"[FALLBACK-VAD] Detecting onset peaks for word boundaries...")
                
                # CHECKPOINT SYSTEM: Track cumulative timing to prevent drift
                expected_words_per_ms = total_words / total_speech_duration
                cumulative_words = 0
                cumulative_time = 0.0
                
                for window_idx, (window_start, window_end) in enumerate(phrase_windows):
                    window_duration = window_end - window_start
                    
                    # Estimate words in this window based on its DURATION proportion
                    remaining_words = total_words - word_idx
                    if remaining_words <= 0:
                        break
                    
                    # Distribute proportionally to DURATION
                    proportion = window_duration / total_speech_duration if total_speech_duration > 0 else 1.0 / len(phrase_windows)
                    words_in_window = max(1, round(total_words * proportion))
                    words_in_window = min(words_in_window, remaining_words)
                    
                    # Last window gets all remaining
                    if window_idx == len(phrase_windows) - 1:
                        words_in_window = remaining_words
                    
                    if words_in_window == 0:
                        continue
                    
                    # IMPROVED APPROACH: Use energy-based segmentation within window
                    # Extract word-length hints to guide distribution
                    window_words = expected_words[word_idx:word_idx + words_in_window]
                    
                    # Calculate target duration per word based on word length
                    # Longer words should get slightly more time
                    word_lengths = [len(w) for w in window_words]
                    total_length = sum(word_lengths)
                    
                    if total_length == 0:
                        # Fallback to uniform
                        word_durations = [window_duration / words_in_window] * words_in_window
                    else:
                        # Distribute proportionally to word length, but not too extreme
                        # Use sqrt to dampen the effect (so "o" vs "modelagem" isn't 1:9 ratio)
                        import math
                        sqrt_lengths = [math.sqrt(length) for length in word_lengths]
                        total_sqrt = sum(sqrt_lengths)
                        word_durations = [(sqrt_len / total_sqrt) * window_duration for sqrt_len in sqrt_lengths]
                    
                    # Now detect energy peaks to adjust positions slightly
                    start_sample = int((window_start / 1000.0) * sample_rate)
                    end_sample = int((window_end / 1000.0) * sample_rate)
                    window_audio = audio[start_sample:end_sample]
                    
                    # Calculate energy envelope
                    try:
                        import librosa
                        # Use RMS energy with small hop for better resolution
                        energy = librosa.feature.rms(y=window_audio, frame_length=512, hop_length=128)[0]
                        
                        # Find peaks in energy (potential word starts)
                        from scipy.signal import find_peaks
                        peaks, properties = find_peaks(energy, distance=int(0.1 * len(energy) / words_in_window))
                        
                        # Convert peak frames to milliseconds
                        hop_ms = (128 / sample_rate) * 1000
                        peak_positions = [window_start + (p * hop_ms) for p in peaks]
                        
                        print(f"[FALLBACK-VAD] Window {window_idx}: {window_duration:.0f}ms, {words_in_window} words (ENERGY-GUIDED, {len(peaks)} peaks)")
                    except Exception as e:
                        print(f"[FALLBACK-VAD] Window {window_idx}: {window_duration:.0f}ms, {words_in_window} words (LENGTH-BASED, error: {e})")
                        peak_positions = []
                    
                    # CHECKPOINT: Before distributing, check if we need to adjust for drift
                    # Expected cumulative progress vs actual window position
                    expected_cumulative_time = cumulative_words / expected_words_per_ms
                    actual_cumulative_time = window_start
                    drift_at_window = actual_cumulative_time - expected_cumulative_time
                    
                    # OPTIMIZED drift correction: balanced adjustments
                    if abs(drift_at_window) > 1000 and window_idx > 0:
                        # Calculate correction factor based on drift magnitude and remaining windows
                        remaining_windows = len(phrase_windows) - window_idx
                        
                        # Base correction: 8% (gentle but effective)
                        correction_factor = 0.08
                        
                        # Boost for large drift
                        if abs(drift_at_window) > 4000:
                            correction_factor = 0.18  # 18% for severe drift
                        elif abs(drift_at_window) > 2500:
                            correction_factor = 0.12  # 12% for moderate drift
                        
                        # Final windows get boost to ensure we end well
                        if remaining_windows <= 2:
                            correction_factor = min(0.18, correction_factor + 0.04)  # Max 18% correction
                        
                        correction = -drift_at_window * correction_factor
                        adjusted_window_start = window_start + correction
                        adjusted_window_end = window_end + correction
                        adjusted_window_duration = adjusted_window_end - adjusted_window_start
                        
                        print(f"[CHECKPOINT] Window {window_idx}/{len(phrase_windows)}: drift={drift_at_window:.0f}ms, factor={correction_factor:.0%}, correction={correction:.0f}ms")
                        
                        # Recalculate word durations with adjusted window
                        if total_length > 0:
                            word_durations = [(sqrt_len / total_sqrt) * adjusted_window_duration for sqrt_len in sqrt_lengths]
                        else:
                            word_durations = [adjusted_window_duration / words_in_window] * words_in_window
                        
                        window_start = adjusted_window_start
                        window_end = adjusted_window_end
                        window_duration = adjusted_window_duration
                    
                    # Distribute words using calculated durations
                    current_pos = window_start
                    for i in range(words_in_window):
                        if word_idx >= len(expected_words):
                            break
                        
                        word_start = current_pos
                        word_end = min(current_pos + word_durations[i], window_end)
                        
                        # If we have peaks, try to snap word_start to nearest peak (within 150ms)
                        if peak_positions:
                            nearby_peaks = [p for p in peak_positions if abs(p - word_start) < 150]
                            if nearby_peaks:
                                word_start = min(nearby_peaks, key=lambda p: abs(p - word_start))
                        
                        token = AlignmentToken(
                            type=TokenType.WORD,
                            text=expected_words[word_idx],
                            viseme=self._text_to_viseme(expected_words[word_idx]),
                            start_ms=word_start,
                            end_ms=word_end,
                            confidence=0.7,
                            lang=language
                        )
                        tokens.append(token)
                        current_pos = word_end
                        word_idx += 1
                        cumulative_words += 1
                    
                    # Update cumulative time tracker
                    cumulative_time = window_end
                
                # Handle remaining words
                if word_idx < len(expected_words):
                    last_end = tokens[-1].end_ms if tokens else 0.0
                    for i in range(word_idx, len(expected_words)):
                        start_ms = last_end + (i - word_idx) * 150
                        end_ms = start_ms + 150
                        token = AlignmentToken(
                            type=TokenType.WORD,
                            text=expected_words[i],
                            viseme=self._text_to_viseme(expected_words[i]),
                            start_ms=start_ms,
                            end_ms=end_ms,
                            confidence=0.5,
                            lang=language
                        )
                        tokens.append(token)
                
                # FINAL VALIDATION: Gentle stretch to eliminate remaining drift
                if tokens and phrase_windows:
                    word_tokens = [t for t in tokens if t.type.value == 'word']
                    if word_tokens:
                        last_word = word_tokens[-1]
                        last_window_end = phrase_windows[-1][1]
                        actual_end = last_word.end_ms
                        expected_end = last_window_end  # Should match last VAD window
                        drift = actual_end - expected_end
                        
                        # Stretch if drift > 700ms (catch remaining drift)
                        if abs(drift) > 700:
                            # Adjust only last 15% of tokens (was 30%), minimum 3 tokens
                            num_tokens_to_adjust = max(3, int(len(word_tokens) * 0.15))
                            tokens_to_adjust = word_tokens[-num_tokens_to_adjust:]
                            anchor_time = tokens_to_adjust[0].start_ms
                            
                            current_span = last_word.end_ms - anchor_time
                            target_span = expected_end - anchor_time
                            stretch_factor = target_span / current_span if current_span > 0 else 1.0
                            
                            print(f"[FINAL-STRETCH] Drift={drift:.0f}ms, gently stretching last {num_tokens_to_adjust} tokens by {stretch_factor:.3f}x")
                            
                            # Apply proportional stretch/compress
                            for token in tokens_to_adjust:
                                token.start_ms = anchor_time + (token.start_ms - anchor_time) * stretch_factor
                                token.end_ms = anchor_time + (token.end_ms - anchor_time) * stretch_factor
                            
                            actual_end = word_tokens[-1].end_ms
                            drift = actual_end - expected_end
                        
                        # Final report
                        if abs(drift) > 500:
                            print(f"[TIMING] Final timing: {actual_end:.0f}ms / {expected_end:.0f}ms (drift={drift:.0f}ms)")
                        else:
                            print(f"[TIMING] ✅ Alignment complete: {actual_end:.0f}ms / {expected_end:.0f}ms (drift={drift:.0f}ms)")
                
                # Add GAP tokens
                for gap_start, gap_end in gaps:
                    gap_token = AlignmentToken(
                        type=TokenType.GAP,
                        text="",
                        viseme="neutral",
                        start_ms=gap_start,
                        end_ms=gap_end,
                        confidence=1.0,
                        lang=language
                    )
                    tokens.append(gap_token)
                
                tokens.sort(key=lambda t: t.start_ms)
                print(f"[FALLBACK-VAD] Generated {len(tokens)} VAD-based tokens")
                return tokens
                
            except Exception as e:
                print(f"[WARNING] VAD-based fallback failed: {e}, using simple distribution")
        
        # Simple linear distribution if VAD not available
        print(f"[FALLBACK-SIMPLE] Using simple word distribution")
        avg_word_duration = audio_duration_ms / len(expected_words)
        tokens = []
        
        for i, word in enumerate(expected_words):
            start_ms = i * avg_word_duration
            end_ms = (i + 1) * avg_word_duration
            
            token = AlignmentToken(
                type=TokenType.WORD,
                text=word,
                viseme=self._text_to_viseme(word),
                start_ms=start_ms,
                end_ms=end_ms,
                confidence=0.5,
                lang=language
            )
            tokens.append(token)
        
        print(f"[FALLBACK-SIMPLE] Generated {len(tokens)} simple tokens")
        return tokens
    
    def _text_to_viseme(self, text: str) -> str:
        """Convert text to viseme using language-specific mapping"""
        if self.language == "pt-BR":
            # Simplified viseme mapping for demo
            # In production, would use proper phonetic analysis
            text_lower = text.lower()
            if any(c in text_lower for c in "aá"):
                return "A"
            elif any(c in text_lower for c in "eé"):
                return "E"
            elif any(c in text_lower for c in "ií"):
                return "I"
            elif any(c in text_lower for c in "oóõ"):
                return "O"
            elif any(c in text_lower for c in "uú"):
                return "U"
            elif any(c in text_lower for c in "mbn"):
                return "M"
            elif any(c in text_lower for c in "fv"):
                return "F"
            elif any(c in text_lower for c in "sz"):
                return "S"
        
        return "neutral"
    
    def calculate_stats(self, tokens: List[AlignmentToken], audio_duration_ms: float) -> AlignmentStats:
        """Calculate quality statistics for alignment result"""
        if not tokens:
            return AlignmentStats(
                audio_ms=audio_duration_ms,
                drift_ms=audio_duration_ms,
                unaligned_count=1,
                avg_confidence=0.0,
                pause_count=0
            )
        
        total_duration = sum(t.end_ms - t.start_ms for t in tokens)
        drift_ms = abs(total_duration - audio_duration_ms)
        
        word_tokens = [t for t in tokens if t.type == TokenType.WORD]
        unaligned_count = len([t for t in word_tokens if t.confidence < 0.5])
        avg_confidence = np.mean([t.confidence for t in word_tokens]) if word_tokens else 0.0
        pause_count = len([t for t in tokens if t.type == TokenType.GAP])
        
        return AlignmentStats(
            audio_ms=audio_duration_ms,
            drift_ms=drift_ms,
            unaligned_count=unaligned_count,
            avg_confidence=avg_confidence,
            pause_count=pause_count
        )
    
    def align_audio_to_text_enhanced(
        self,
        audio_path: str,
        transcript: str,
        granularity: str = "word",
        language: str | None = None,
        fps: float = 30.0,
        method: str = "auto",
        **kwargs,
    ) -> Tuple[AlignmentResult, List["WordTiming"], List["FrameState"]]:
        """
        Enhanced alignment function using advanced components
        
        Args:
            audio_path: Path to audio file
            transcript: Text transcript matching audio
            granularity: "word" or "phoneme" level alignment
            language: Optional language code override
            fps: Frame rate for animation synchronization
            method: Alignment method ("wav2vec2", "whisper", "auto")
            
        Extra kwargs:
            precision: (Deprecated/ignored) Frontend may pass a precision mode string. Timing refinement
                happens downstream; this parameter is accepted for backward compatibility and ignored.

        Returns:
            Tuple of (AlignmentResult, WordTiming list, FrameState list)
        """
        if not self.use_enhanced:
            # Fall back to legacy method
            result = self.align_audio_to_text(audio_path, transcript, granularity, language)
            return result, [], []
        
        print(f"[ROCKET] Enhanced alignment starting for {os.path.basename(audio_path)}")
        
        # Use provided language or fall back to instance language
        use_language = language or self.language

        # 1. Preprocess inputs (audio + text); audio decode can be expensive so keep early
        audio, sample_rate = self.preprocess_audio(audio_path)
        normalized_text = self.preprocess_text(transcript)
        
        try:
            # 2 & 3. Potential parallel execution of silence detection and forced alignment
            from app.core.utils.config import config as _cfg
            do_parallel = False
            try:
                do_parallel = _cfg.features.parallel_enhanced_alignment()
            except Exception:
                pass

            silence_segments = []
            forced_result = None

            def _run_silence():
                nonlocal silence_segments
                print("🔍 Performing enhanced silence detection...")
                if self.silence_detector:
                    silence_segments = self.silence_detector.detect_silence_segments(
                        audio, adaptive_thresholds=True
                    )

            def _run_alignment():
                nonlocal forced_result
                print("[TARGET] Performing forced alignment...")
                if not self.forced_aligner:
                    raise RuntimeError("Forced aligner not available")
                forced_result = self.forced_aligner.align_text_to_audio(
                    audio, normalized_text, sample_rate, method=method
                )

            if do_parallel:
                t1 = threading.Thread(target=_run_silence, name="silence-detector")
                t2 = threading.Thread(target=_run_alignment, name="forced-aligner")
                t1.start(); t2.start(); t1.join(); t2.join()
            else:
                _run_silence()
                _run_alignment()
            
            # 4. Create precise frame timeline
            print("[CLAPPER] Creating frame synchronization timeline...")
            
            # Update frame synchronizer FPS
            if not self.frame_synchronizer:
                raise RuntimeError("Frame synchronizer not available")
            self.frame_synchronizer.fps = fps  # type: ignore[attr-defined]
            self.frame_synchronizer.frame_duration = 1.0 / fps  # type: ignore[attr-defined]
            
            # Convert forced alignment to word timings
            word_timings_list = [
                (token.text, token.start_time, token.end_time)
                for token in getattr(forced_result, 'tokens', [])
            ]
            confidence_scores = [
                token.confidence for token in getattr(forced_result, 'tokens', [])
            ]
            
            # Create timeline with sub-frame precision including silence segments
            timeline = self.frame_synchronizer.create_animation_timeline(  # type: ignore[call-arg]
                word_timings_list,
                getattr(forced_result, 'total_duration', len(audio) / sample_rate),
                confidence_scores,
                silence_segments,
            )
            
            # Optimize timeline
            timeline = self.frame_synchronizer.optimize_timeline(timeline)  # type: ignore[arg-type]
            
            # 5. Generate frame sequence
            print("🎭 Generating frame sequence...")
            frame_states = self.frame_synchronizer.generate_frame_sequence(  # type: ignore[arg-type]
                timeline, getattr(forced_result, 'total_duration', len(audio) / sample_rate)
            )
            
            # 6. Convert to legacy AlignmentResult format for compatibility
            legacy_tokens = []
            
            # Add silence gaps as GAP tokens
            for seg in silence_segments:
                legacy_tokens.append(AlignmentToken(
                    type=TokenType.GAP,
                    text="",
                    viseme="REST",
                    start_ms=seg.start_time * 1000,
                    end_ms=seg.end_time * 1000,
                    confidence=seg.confidence,
                    lang=use_language
                ))
            
            # Add word tokens
            for token in getattr(forced_result, 'tokens', []):
                legacy_tokens.append(AlignmentToken(
                    type=TokenType.WORD,
                    text=token.text,
                    viseme=self._map_to_viseme(token.text),
                    start_ms=token.start_time * 1000,
                    end_ms=token.end_time * 1000,
                    confidence=token.confidence,
                    lang=use_language
                ))
            
            # Sort by start time
            legacy_tokens.sort(key=lambda x: x.start_ms)

            # Reconcile with transcript similarly to the legacy path and insert VAD gaps again
            try:
                reconciled = self._reconcile_with_transcript(legacy_tokens, normalized_text, [(s.start_time*1000, s.end_time*1000) for s in silence_segments])
                # Merge with explicit gap tokens for downstream consumers
                merged_tokens: List[AlignmentToken] = []
                for seg in silence_segments:
                    merged_tokens.append(AlignmentToken(
                        type=TokenType.GAP,
                        text="",
                        viseme="neutral",
                        start_ms=seg.start_time*1000,
                        end_ms=seg.end_time*1000,
                        confidence=1.0,
                        lang=use_language,
                    ))
                merged_tokens.extend(reconciled)
                merged_tokens.sort(key=lambda t: t.start_ms)
                legacy_tokens = merged_tokens
            except Exception as _e:
                print(f"[WARNING] Enhanced reconcile skipped: {_e}")
            
            # Calculate stats
            audio_duration_ms = forced_result.total_duration * 1000
            stats = self._calculate_enhanced_stats(legacy_tokens, silence_segments, forced_result)
            
            result = AlignmentResult(
                language=use_language,
                sample_rate=sample_rate,
                tokens=legacy_tokens,
                stats=stats
            )
            
            print(f"[CHECK] Enhanced alignment completed successfully")
            print(f"[CHART] Results: {len(forced_result.tokens)} words, {len(silence_segments)} silence segments")
            print(f"[CLAPPER] Generated {len(frame_states)} frame states at {fps} FPS")
            
            return result, timeline, frame_states
            
        except Exception as e:
            print(f"[X] Enhanced alignment failed: {e}")
            print("[REFRESH] Falling back to legacy alignment")
            
            # Fall back to legacy method
            result = self.align_audio_to_text(audio_path, transcript, granularity, language)
            return result, [], []
    
    def align_audio_to_text(self, audio_path: str, transcript: str, 
                          granularity: str = "word", language: str = None,
                          char_level: bool = False) -> AlignmentResult:
        """
        Main alignment function - align audio to transcript
        
        Args:
            audio_path: Path to audio file
            transcript: Text transcript matching audio
            granularity: "word" or "phoneme" level alignment
            language: Optional language code override (defaults to instance language)
        """
        # Use the provided audio file directly
                
        # Use provided language or fall back to instance language
        use_language = language or self.language
        # 1. Preprocess inputs
        audio, sample_rate = self.preprocess_audio(audio_path)
        
        # Log original transcript word count
        import re
        original_words = [w for w in re.findall(r"\w+", transcript, flags=re.UNICODE) if w.strip()]
        print(f"[TRANSCRIPT] Original: {len(transcript)} chars, {len(original_words)} words")
        
        normalized_text = self.preprocess_text(transcript)
        normalized_words = [w for w in re.findall(r"\w+", normalized_text, flags=re.UNICODE) if w.strip()]
        print(f"[TRANSCRIPT] Normalized: {len(normalized_text)} chars, {len(normalized_words)} words")
        
        try:
            # 2. Perform alignment
            alignment_result = self.align_with_whisperx(audio, normalized_text)
            
            # Check if alignment was successful (has words)
            has_aligned_words = False
            for segment in alignment_result.get("segments", []):
                if segment.get("words") and len(segment.get("words")) > 0:
                    has_aligned_words = True
                    break
                    
            if not has_aligned_words:
                raise Exception("No aligned words found in alignment result")
                
            # 3. Detect gaps
            gaps = self.detect_gaps_with_vad(audio, sample_rate)
            
            # 4. Merge tokens and gaps (with transcript reconciliation to avoid drift)
            tokens = self.merge_tokens_and_gaps(alignment_result, gaps, normalized_text)
            
        except Exception as e:
            print(f"[WARNING] Alignment failed: {e}")
            print("[REFRESH] Falling back to VAD-based token generation")
            
            # Generate tokens based on VAD + transcript (NEW: passes audio for VAD!)
            audio_duration_ms = len(audio) / sample_rate * 1000
            tokens = self.generate_text_based_tokens(normalized_text, audio_duration_ms, use_language, audio, sample_rate)
            gaps = []
        
        # If user explicitly disabled char-level, collapse any character tokens back into words
        if not char_level:
            tokens = self._collapse_char_tokens_into_words(tokens)

        # 5. Calculate quality stats
        stats = self.calculate_stats(tokens, audio_duration_ms=len(audio) / sample_rate * 1000)
        
        return AlignmentResult(
            language=use_language,
            sample_rate=sample_rate,
            tokens=tokens,
            stats=stats
        )

    def _collapse_char_tokens_into_words(self, tokens: List[AlignmentToken]) -> List[AlignmentToken]:
        """Collapse consecutive single-letter WORD tokens back into full words.
        Keeps timing from first to last char; merges gaps appropriately.
        """
        if not tokens:
            return tokens
        merged: List[AlignmentToken] = []
        buffer_word = []  # type: List[AlignmentToken]
        def flush_buffer():
            nonlocal buffer_word
            if not buffer_word:
                return
            start = buffer_word[0].start_ms
            end = buffer_word[-1].end_ms
            text = ''.join(t.text for t in buffer_word)
            merged.append(AlignmentToken(
                type=buffer_word[0].type,
                text=text,
                viseme=self._text_to_viseme(text),
                start_ms=start,
                end_ms=end,
                confidence=min((t.confidence for t in buffer_word if hasattr(t, 'confidence')), default=0.7),
                lang=buffer_word[0].lang,
            ))
            buffer_word = []

        for t in tokens:
            if t.type == TokenType.WORD and len(t.text) == 1 and t.text.isalpha():
                buffer_word.append(t)
                continue
            # non char token
            flush_buffer()
            merged.append(t)
        flush_buffer()
        # Merge small adjacent gaps if needed (optional)
        out: List[AlignmentToken] = []
        for t in merged:
            if out and t.type == TokenType.GAP and out[-1].type == TokenType.GAP:
                out[-1].end_ms = t.end_ms
            else:
                out.append(t)
        return out
    
    def export_for_face_sequencer(self, result: AlignmentResult) -> Dict:
        """
        Convert AlignmentResult to Face Sequencer timeline format
        
        Args:
            result: AlignmentResult from alignment
            
        Returns:
            Dictionary compatible with Face Sequencer timeline
        """
        timeline_events = []
        
        for token in result.tokens:
            if token.type == TokenType.GAP:
                # Add pause/neutral frame for gaps
                timeline_events.append({
                    "time_ms": token.start_ms,
                    "event": "set_viseme", 
                    "value": "neutral",
                    "duration_ms": token.end_ms - token.start_ms
                })
            else:
                # Add viseme for words/phonemes
                timeline_events.append({
                    "time_ms": token.start_ms,
                    "event": "set_viseme",
                    "value": token.viseme,
                    "duration_ms": token.end_ms - token.start_ms,
                    "text": token.text,
                    "confidence": token.confidence
                })
        
        return {
            "timeline": timeline_events,
            "metadata": {
                "language": result.language,
                "sample_rate": result.sample_rate,
                "total_duration_ms": result.stats.audio_ms,
                "stats": asdict(result.stats)
            }
        }
    
    def _map_to_viseme(self, text: str) -> str:
        """Map text to viseme using Portuguese phoneme rules"""
        if not text or not text.strip():
            return "REST"
        
        # Simple mapping based on first character - would be enhanced with phoneme analysis
        first_char = text.strip()[0].lower()
        
        if self.language.startswith("pt"):
            viseme_map = self.pt_br_config["phoneme_to_viseme"]
            return viseme_map.get(first_char, "A")  # Default to 'A' for unknown
        else:
            # Basic English mapping
            if first_char in 'aeiouáéíóúãõ':
                return first_char.upper()
            elif first_char in 'pb':
                return "P"
            elif first_char in 'fv':
                return "F"
            elif first_char in 'td':
                return "T"
            else:
                return "REST"
    
    def _calculate_enhanced_stats(self, tokens: List[AlignmentToken], 
                                silence_segments: List, forced_result) -> AlignmentStats:
        """Calculate statistics for enhanced alignment"""
        if not tokens:
            return AlignmentStats(
                audio_ms=0, drift_ms=0, unaligned_count=0, 
                avg_confidence=0, pause_count=0
            )
        
        # Calculate timing stats
        audio_ms = forced_result.total_duration * 1000
        confidences = [token.confidence for token in tokens if token.type == TokenType.WORD]
        avg_confidence = np.mean(confidences) if confidences else 0.0
        
        # Count unaligned tokens (low confidence)
        unaligned_count = sum(1 for c in confidences if c < 0.5)
        
        # Pause count from silence segments
        pause_count = len(silence_segments)
        
        # Calculate drift (simplified)
        drift_ms = 0.0
        if len(tokens) > 1:
            expected_duration = (tokens[-1].end_ms - tokens[0].start_ms)
            actual_duration = audio_ms
            drift_ms = abs(expected_duration - actual_duration)
        
        return AlignmentStats(
            audio_ms=audio_ms,
            drift_ms=drift_ms,
            unaligned_count=unaligned_count,
            avg_confidence=avg_confidence,
            pause_count=pause_count
        )


# Example usage and testing functions
def test_portuguese_alignment():
    """Test function for Portuguese audio alignment"""
    aligner = AudioAligner(language="pt-BR")
    
    # Example Portuguese text
    text = """Olá, como você está hoje? 
    Vamos fazer um projeto incrível juntos!
    Este é um teste de alinhamento de áudio."""
    
    # Note: This would need actual audio file
    # result = aligner.align_audio_to_text("portuguese_sample.wav", text)
    # face_sequencer_data = aligner.export_for_face_sequencer(result)
    # print(json.dumps(face_sequencer_data, indent=2, ensure_ascii=False))
    
    print("Portuguese aligner initialized successfully")
    print(f"Language: {aligner.language}")
    print(f"Device: {aligner.device}")
    print("Ready for audio processing!")

if __name__ == "__main__":
    test_portuguese_alignment()