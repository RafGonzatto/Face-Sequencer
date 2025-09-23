# audio_aligner.py - Audio-driven animation timing for Face Sequencer Pro
"""
Audio alignment system for Portuguese-first lip-sync animation.
Derives precise word/phoneme timings from audio using forced alignment.
"""

import os
import librosa
import numpy as np
import json
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

# Import PyTorch 2.6 compatibility patch
try:
    from torch_patch import patch_torch_for_whisperx
except ImportError:
    # Define a no-op function if the patch isn't available
    def patch_torch_for_whisperx():
        print("⚠️ Warning: torch_patch not found, WhisperX might fail with PyTorch 2.6+")
        pass
        pass

# Import enhanced components
try:
    from enhanced_silence_detector import EnhancedSilenceDetector
    from forced_alignment import ForcedAligner, AlignmentResult as ForcedAlignmentResult
    from frame_synchronizer import PreciseFrameSynchronizer, WordTiming, FrameState
    ENHANCED_COMPONENTS_AVAILABLE = True
    print("✅ Enhanced audio alignment components loaded")
except ImportError as e:
    print(f"⚠️ Enhanced components not available: {e}")
    print("📝 Using legacy audio alignment methods")
    ENHANCED_COMPONENTS_AVAILABLE = False

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
    
# Apply direct PyTorch patch for WhisperX
try:
    import torch
    if hasattr(torch, "__version__"):
        version = torch.__version__
        if version.startswith("2.6") or version.startswith("2.7"):
            # Override torch.load to always use weights_only=False for compatibility
            original_torch_load = torch.load
            def patched_torch_load(f, *args, **kwargs):
                # Always use weights_only=False regardless of what's passed
                kwargs_copy = {k: v for k, v in kwargs.items() if k != 'weights_only'}
                kwargs_copy['weights_only'] = False
                print("🔄 Using patched torch.load with weights_only=False")
                return original_torch_load(f, *args, **kwargs_copy)
            
            # Apply the patch
            torch.load = patched_torch_load
            print(f"✅ PyTorch {version} patched for WhisperX compatibility")
except Exception as e:
    print(f"⚠️ Failed to apply PyTorch patch: {e}")

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
    """
    
    def __init__(self, language: str = "pt-BR", device: str = "auto"):
        self.language = language
        self.device = self._setup_device(device)
        self.models = {}
        
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
        
        # Initialize enhanced components if available
        if ENHANCED_COMPONENTS_AVAILABLE:
            self.silence_detector = EnhancedSilenceDetector(sample_rate=16000)
            self.forced_aligner = ForcedAligner(device=device, language=language[:2])
            self.frame_synchronizer = PreciseFrameSynchronizer(fps=30.0)
            self.use_enhanced = True
            print("✅ Enhanced alignment components initialized")
        else:
            self.use_enhanced = False
            print("📝 Using legacy alignment methods")
        
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
        # Load audio as mono 16kHz (standard for speech processing)
        print(f"🔊 Loading and preprocessing audio: {os.path.basename(audio_path)}")
        audio, sr = librosa.load(audio_path, sr=16000, mono=True)
        
        # Check audio levels
        rms = np.sqrt(np.mean(audio**2))
        print(f"📊 Audio RMS level before processing: {rms:.4f}")
        
        # Strong normalization for low-level audio
        audio = librosa.util.normalize(audio) * 0.95
        
        # Enhanced denoising - reduce background noise
        audio = librosa.effects.preemphasis(audio, coef=0.97)
        
        # Light processing for ElevenLabs audio - preserve silences for gap detection
        if "ElevenLabs" in audio_path:
            print("📝 Detected ElevenLabs audio - applying specialized processing (preserving pauses)")
            # NO trimming - preserve all audio including silences for gap detection
            
            # Apply only gentle high-pass filter to remove rumble
            from scipy.signal import butter, filtfilt
            nyq = 0.5 * sr
            cutoff = 80 / nyq  # 80Hz high-pass
            b, a = butter(3, cutoff, btype='high')
            audio = filtfilt(b, a, audio)
        else:
            # Standard light trimming for other audio sources
            audio, _ = librosa.effects.trim(audio, top_db=30)  # More conservative trimming
        
        # Final check of audio levels after processing
        rms_after = np.sqrt(np.mean(audio**2))
        print(f"📊 Audio RMS level after processing: {rms_after:.4f}")
        
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
        # Try to import our compatibility module first
        try:
            import whisperx_compat as whisperx
            print("✅ Using WhisperX compatibility layer for PyTorch 2.6+")
        except ImportError:
            # Fall back to regular import with patch
            patch_torch_for_whisperx()
            try:
                import whisperx
            except ImportError:
                raise ImportError("whisperx not installed. Run: pip install whisperx")
        
        # Load models if not cached
        if 'transcribe' not in self.models:
            # Use the tiny model for faster processing and lower memory usage
            print("🔄 Loading WhisperX transcription model (first run may take longer)...")
            self.models['transcribe'] = whisperx.load_model(
                "tiny", self.device, compute_type="int8"
            )
            print("✅ WhisperX transcription model loaded")
        
        if 'align' not in self.models:
            print(f"🔄 Loading alignment model for language {self.language[:2]}...")
            try:
                self.models['align'], self.models['align_meta'] = whisperx.load_align_model(
                    language_code=self.language[:2], device=self.device  # pt-BR -> pt
                )
                print("✅ Alignment model loaded")
            except Exception as e:
                print(f"⚠️ Error loading alignment model: {e}")
                print(f"🔄 Falling back to word-level alignment only")
                # Set dummy alignment model and metadata
                self.models['align'] = None
                self.models['align_meta'] = None
        
        # Initial transcription with word timestamps
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
                print(f"⚠️ Error during alignment: {e}")
                print(f"🔄 Using only word-level timing from transcription")
                # Just use the original transcription result if alignment fails
                aligned_result = result
        else:
            # If alignment model couldn't be loaded, just use the transcription result
            print(f"🔄 Using only word-level timing from transcription (no alignment model)")
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
                    if gap_duration >= 80:  # Minimum gap duration
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
                if gap_duration >= 80:  # Minimum gap duration
                    gaps.append((gap_start, time * 1000))
                gap_start = None
        
        return gaps
    
    def merge_tokens_and_gaps(self, alignment_result: Dict, gaps: List[Tuple[float, float]]) -> List[AlignmentToken]:
        """
        Merge aligned words with detected gaps into unified token stream
        
        Args:
            alignment_result: WhisperX alignment result
            gaps: List of gap intervals from VAD
            
        Returns:
            List of AlignmentTokens including words and gaps
        """
        tokens = []
        
        # Extract words from alignment result
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
                tokens.append(token)
        
        # Insert gaps
        all_tokens = []
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
        all_tokens.extend(tokens)
        all_tokens.sort(key=lambda t: t.start_ms)
        
        return all_tokens
    
    def generate_text_based_tokens(self, text: str, audio_duration_ms: float, language: str) -> List[AlignmentToken]:
        """
        Generate alignment tokens based solely on the text and audio duration.
        This is a fallback method when forced alignment fails.
        
        Args:
            text: Text to convert to tokens
            audio_duration_ms: Total audio duration in milliseconds
            language: Language code
            
        Returns:
            List of AlignmentToken objects
        """
        print(f"🔄 Generating text-based tokens for {len(text)} characters over {audio_duration_ms:.2f}ms")
        
        # Split text into words, preserving punctuation
        import re
        words = re.findall(r'\w+|[^\w\s]', text)
        words = [w for w in words if w.strip()]  # Remove empty strings
        
        # If no words, return single token for the whole duration
        if not words:
            return [AlignmentToken(
                type=TokenType.WORD,
                text=text or "silence",
                viseme=self._text_to_viseme(text or "A"),
                start_ms=0,
                end_ms=audio_duration_ms,
                confidence=0.5,
                lang=language
            )]
        
        # Calculate average duration per word
        avg_word_duration = audio_duration_ms / len(words)
        
        # Add small pauses between words (20% of average word duration)
        pause_duration = min(max(avg_word_duration * 0.2, 50), 300)  # Between 50-300ms
        
        # Recalculate word duration to account for pauses
        total_pause_duration = pause_duration * (len(words) - 1)
        word_duration = (audio_duration_ms - total_pause_duration) / len(words)
        
        tokens = []
        current_time = 0
        
        for i, word in enumerate(words):
            # For each individual word, generate separate tokens for each character
            # This will give us better visual results when alignment fails
            if len(word) > 1 and word.isalpha():
                # Calculate duration for each character in the word
                char_duration = word_duration / len(word)
                
                for char in word:
                    char_token = AlignmentToken(
                        type=TokenType.WORD,
                        text=char,  # Individual character
                        viseme=self._text_to_viseme(char),
                        start_ms=current_time,
                        end_ms=current_time + char_duration,
                        confidence=0.7,
                        lang=language
                    )
                    tokens.append(char_token)
                    current_time += char_duration
            else:
                # For punctuation or single characters, use the entire word
                word_token = AlignmentToken(
                    type=TokenType.WORD,
                    text=word,
                    viseme=self._text_to_viseme(word),
                    start_ms=current_time,
                    end_ms=current_time + word_duration,
                    confidence=0.7,  # Confidence for generated tokens
                    lang=language
                )
                tokens.append(word_token)
                current_time += word_duration
            
            # Add pause token except after the last word
            if i < len(words) - 1:
                pause_token = AlignmentToken(
                    type=TokenType.GAP,
                    text="",
                    viseme="neutral",
                    start_ms=current_time,
                    end_ms=current_time + pause_duration,
                    confidence=1.0,
                    lang=language
                )
                tokens.append(pause_token)
                current_time += pause_duration
        
        print(f"✅ Generated {len(tokens)} text-based tokens ({len([t for t in tokens if t.type == TokenType.WORD])} words)")
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
    
    def align_audio_to_text_enhanced(self, audio_path: str, transcript: str, 
                                   granularity: str = "word", language: str = None,
                                   fps: float = 30.0, method: str = "auto") -> Tuple[AlignmentResult, List[WordTiming], List[FrameState]]:
        """
        Enhanced alignment function using advanced components
        
        Args:
            audio_path: Path to audio file
            transcript: Text transcript matching audio
            granularity: "word" or "phoneme" level alignment
            language: Optional language code override
            fps: Frame rate for animation synchronization
            method: Alignment method ("wav2vec2", "whisper", "auto")
            
        Returns:
            Tuple of (AlignmentResult, WordTiming list, FrameState list)
        """
        if not self.use_enhanced:
            # Fall back to legacy method
            result = self.align_audio_to_text(audio_path, transcript, granularity, language)
            return result, [], []
        
        print(f"🚀 Enhanced alignment starting for {os.path.basename(audio_path)}")
        
        # Use provided language or fall back to instance language
        use_language = language or self.language
        
        # 1. Preprocess inputs
        audio, sample_rate = self.preprocess_audio(audio_path)
        normalized_text = self.preprocess_text(transcript)
        
        try:
            # 2. Enhanced silence detection
            print("🔍 Performing enhanced silence detection...")
            silence_segments = self.silence_detector.detect_silence_segments(
                audio, adaptive_thresholds=True
            )
            
            # 3. Forced alignment with transformer models
            print("🎯 Performing forced alignment...")
            forced_result = self.forced_aligner.align_text_to_audio(
                audio, normalized_text, sample_rate, method=method
            )
            
            # 4. Create precise frame timeline
            print("🎬 Creating frame synchronization timeline...")
            
            # Update frame synchronizer FPS
            self.frame_synchronizer.fps = fps
            self.frame_synchronizer.frame_duration = 1.0 / fps
            
            # Convert forced alignment to word timings
            word_timings_list = [
                (token.text, token.start_time, token.end_time) 
                for token in forced_result.tokens
            ]
            confidence_scores = [token.confidence for token in forced_result.tokens]
            
            # Create timeline with sub-frame precision including silence segments
            timeline = self.frame_synchronizer.create_animation_timeline(
                word_timings_list, 
                forced_result.total_duration,
                confidence_scores,
                silence_segments
            )
            
            # Optimize timeline
            timeline = self.frame_synchronizer.optimize_timeline(timeline)
            
            # 5. Generate frame sequence
            print("🎭 Generating frame sequence...")
            frame_states = self.frame_synchronizer.generate_frame_sequence(
                timeline, forced_result.total_duration
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
            for token in forced_result.tokens:
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
            
            # Calculate stats
            audio_duration_ms = forced_result.total_duration * 1000
            stats = self._calculate_enhanced_stats(legacy_tokens, silence_segments, forced_result)
            
            result = AlignmentResult(
                language=use_language,
                sample_rate=sample_rate,
                tokens=legacy_tokens,
                stats=stats
            )
            
            print(f"✅ Enhanced alignment completed successfully")
            print(f"📊 Results: {len(forced_result.tokens)} words, {len(silence_segments)} silence segments")
            print(f"🎬 Generated {len(frame_states)} frame states at {fps} FPS")
            
            return result, timeline, frame_states
            
        except Exception as e:
            print(f"❌ Enhanced alignment failed: {e}")
            print("🔄 Falling back to legacy alignment")
            
            # Fall back to legacy method
            result = self.align_audio_to_text(audio_path, transcript, granularity, language)
            return result, [], []
    
    def align_audio_to_text(self, audio_path: str, transcript: str, 
                          granularity: str = "word", language: str = None) -> AlignmentResult:
        """
        Main alignment function - align audio to transcript
        
        Args:
            audio_path: Path to audio file
            transcript: Text transcript matching audio
            granularity: "word" or "phoneme" level alignment
            language: Optional language code override (defaults to instance language)
            
        Returns:
            AlignmentResult with tokens and quality stats
        """
        # Special case for ElevenLabs audio
        if "ElevenLabs" in audio_path:
            print("⚠️ ElevenLabs audio detected - using pre-processed version if available")
            # Check for pre-processed version
            optimized_path = "uploads/audio/optimized_elevenlabs.wav"
            if os.path.exists(optimized_path):
                print("✅ Using optimized audio file")
                audio_path = optimized_path
                
        # Use provided language or fall back to instance language
        use_language = language or self.language
        
        # 1. Preprocess inputs
        audio, sample_rate = self.preprocess_audio(audio_path)
        normalized_text = self.preprocess_text(transcript)
        
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
            
            # 4. Merge tokens and gaps
            tokens = self.merge_tokens_and_gaps(alignment_result, gaps)
            
        except Exception as e:
            print(f"⚠️ Alignment failed: {e}")
            print("🔄 Falling back to text-based token generation")
            
            # Generate tokens based on the transcript and audio duration
            audio_duration_ms = len(audio) / sample_rate * 1000
            tokens = self.generate_text_based_tokens(normalized_text, audio_duration_ms, use_language)
            gaps = []
        
        # 5. Calculate quality stats
        stats = self.calculate_stats(tokens, audio_duration_ms=len(audio) / sample_rate * 1000)
        
        return AlignmentResult(
            language=use_language,
            sample_rate=sample_rate,
            tokens=tokens,
            stats=stats
        )
    
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