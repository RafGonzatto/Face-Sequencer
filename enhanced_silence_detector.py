# enhanced_silence_detector.py - Advanced Voice Activity Detection
"""
Enhanced silence detection using energy and zero-crossing rate analysis.
Replaces basic amplitude threshold with robust multi-feature VAD.
"""

import numpy as np
from scipy.signal import butter, lfilter
from typing import List, Tuple, Optional

# WP001: ensure dataclass decorator is available even in constrained runtimes.
try:
    from dataclasses import dataclass
except ImportError:  # extremely rare on supported Python versions, but fail gracefully
    def dataclass(cls):  # type: ignore
        return cls
    print("Warning: dataclasses module unavailable; proceeding without dataclass features")

@dataclass
class SilenceSegment:
    """Represents a detected silence segment"""
    start_time: float
    end_time: float
    confidence: float
    duration: float
    
    def __post_init__(self):
        self.duration = self.end_time - self.start_time

class EnhancedSilenceDetector:
    """
    Advanced Voice Activity Detection using multiple acoustic features:
    - Short-time energy
    - Zero-crossing rate  
    - Spectral centroid (optional)
    - Smoothing and hysteresis for stability
    """
    
    def __init__(self, sample_rate: Optional[int] = None):
        # Import config here to avoid circular imports
        from config import config
        
        # Use provided sample_rate or get from config
        self.sample_rate = sample_rate if sample_rate is not None else config.audio.sample_rate()
        
        # Get frame parameters from config
        self.frame_length = int(config.audio.silence_frame_length_ms() * 0.001 * self.sample_rate)
        self.frame_shift = int(config.audio.silence_frame_shift_ms() * 0.001 * self.sample_rate)
        
        # Get threshold parameters from config
        self.energy_threshold = config.audio.silence_energy_threshold()
        self.zcr_threshold = config.audio.silence_zcr_threshold()
        self.noise_floor_energy = config.audio.silence_noise_floor()
        self.energy_ceiling = config.audio.silence_energy_ceiling()
        
        # Smoothing parameters
        self.min_silence_duration = 0.1  # 100ms minimum silence
        self.min_speech_duration = 0.05  # 50ms minimum speech
        self.smoothing_window = 5        # frames for median filtering
        
    def detect_silence_segments(self, 
                              audio_data: np.ndarray,
                              energy_threshold: Optional[float] = None,
                              zcr_threshold: Optional[float] = None,
                              adaptive_thresholds: bool = True) -> List[SilenceSegment]:
        """
        Detect silence segments using multi-feature analysis
        
        Args:
            audio_data: Input audio signal
            energy_threshold: Manual energy threshold (if not adaptive)
            zcr_threshold: Manual ZCR threshold (if not adaptive)
            adaptive_thresholds: Whether to compute thresholds from audio stats
            
        Returns:
            List of detected silence segments
        """
        if len(audio_data) == 0:
            return []
            
        print(f"🔍 Analyzing {len(audio_data)/self.sample_rate:.2f}s of audio for silence detection")
        
        # Normalize audio prior to feature extraction
        normalized_audio = self._normalize_audio(audio_data)
        
        # Calculate acoustic features
        energy = self._calculate_energy(normalized_audio)
        zcr = self._calculate_zcr(normalized_audio)
        
        # Adaptive threshold computation
        if adaptive_thresholds:
            self.energy_threshold = self._compute_adaptive_energy_threshold(energy)
            self.zcr_threshold = self._compute_adaptive_zcr_threshold(zcr)
            print(f"📊 Adaptive thresholds - Energy: {self.energy_threshold:.4f}, ZCR: {self.zcr_threshold:.4f}")
        else:
            self.energy_threshold = energy_threshold or self.energy_threshold
            self.zcr_threshold = zcr_threshold or self.zcr_threshold
        
        # Combined silence decision
        silence_mask = self._make_silence_decisions(energy, zcr)
        
        # Smooth decisions to avoid rapid transitions
        smoothed_mask = self._smooth_silence_decisions(silence_mask)
        
        # Convert frame-level decisions to time segments
        silence_segments = self._frames_to_segments(smoothed_mask, energy, zcr)
        
        print(f"✅ Detected {len(silence_segments)} silence segments")
        return silence_segments

    def _normalize_audio(self, audio: np.ndarray) -> np.ndarray:
        """Normalize audio signal to stabilise feature thresholds."""
        if len(audio) == 0:
            return audio

        # Remove DC offset
        normalized = audio - np.mean(audio)

        # Apply gentle high-pass to remove rumble
        nyquist = 0.5 * self.sample_rate
        cutoff = max(30.0, 1.0)
        if nyquist > cutoff:
            norm_cutoff = cutoff / nyquist
            b, a = butter(2, norm_cutoff, btype='highpass')
            normalized = lfilter(b, a, normalized)

        # Peak normalise to maintain dynamic range without clipping
        peak = np.max(np.abs(normalized))
        if peak > 0:
            normalized = normalized / peak

        return normalized
    
    def _calculate_energy(self, audio: np.ndarray) -> np.ndarray:
        """Calculate short-time energy for each frame"""
        frames = self._frame_audio(audio)
        
        # Use RMS energy (more stable than raw power)
        energy = np.array([np.sqrt(np.mean(frame**2)) for frame in frames])
        
        # Log scale for better dynamic range
        energy = np.log10(energy + 1e-10)  # Add small epsilon to avoid log(0)
        
        return energy
    
    def _calculate_zcr(self, audio: np.ndarray) -> np.ndarray:
        """Calculate zero-crossing rate for each frame"""
        frames = self._frame_audio(audio)
        
        zcr = []
        for frame in frames:
            # Count sign changes
            sign_changes = np.abs(np.diff(np.sign(frame)))
            zcr_value = np.sum(sign_changes) / (2 * len(frame))
            zcr.append(zcr_value)
        
        return np.array(zcr)
    
    def _frame_audio(self, audio: np.ndarray) -> List[np.ndarray]:
        """Split audio into overlapping frames"""
        frames = []
        start = 0
        
        while start + self.frame_length <= len(audio):
            frame = audio[start:start + self.frame_length]
            
            # Apply Hamming window to reduce edge effects
            window = np.hamming(len(frame))
            windowed_frame = frame * window
            
            frames.append(windowed_frame)
            start += self.frame_shift
        
        return frames
    
    def _compute_adaptive_energy_threshold(self, energy: np.ndarray) -> float:
        """Compute adaptive energy threshold based on audio statistics"""
        if len(energy) == 0:
            return self.energy_threshold
        
        # Use percentile-based threshold (more robust than mean)
        noise_floor = np.percentile(energy, 10)
        speech_floor = np.percentile(energy, 60)

        self.noise_floor_energy = noise_floor
        self.energy_ceiling = speech_floor

        # Threshold biased towards silence detection, clamped by dynamic range
        threshold = noise_floor + 0.35 * (speech_floor - noise_floor)
        return float(max(threshold, noise_floor - 0.5))
    
    def _compute_adaptive_zcr_threshold(self, zcr: np.ndarray) -> float:
        """Compute adaptive ZCR threshold"""
        if len(zcr) == 0:
            return self.zcr_threshold
            
        # ZCR threshold based on median + standard deviation
        median_zcr = np.median(zcr)
        std_zcr = np.std(zcr)
        
        # Threshold slightly above median
        threshold = median_zcr + 0.5 * std_zcr
        
        return min(threshold, 0.3)  # Maximum threshold
    
    def _make_silence_decisions(self, energy: np.ndarray, zcr: np.ndarray) -> np.ndarray:
        """Combine energy and ZCR for silence decisions"""
        # Individual feature decisions
        low_energy = energy < self.energy_threshold
        low_zcr = zcr < self.zcr_threshold
        
        # Intelligent approach: Primary reliance on energy, ZCR as refinement
        # For very low energy (real silence), ZCR requirement is relaxed
        very_low_energy = energy < (self.energy_threshold * 0.5)
        
        # Silence if: very low energy OR (low energy AND low ZCR)
        silence_mask = very_low_energy | (low_energy & low_zcr)
        
        return silence_mask
    
    def _smooth_silence_decisions(self, silence_mask: np.ndarray) -> np.ndarray:
        """Smooth binary decisions to avoid rapid transitions"""
        if len(silence_mask) < self.smoothing_window:
            return silence_mask
        
        # Use a rolling mean (convolution) for smoothing to avoid SciPy median filter quirks
        window = self.smoothing_window
        kernel = np.ones(window, dtype=float) / window
        # Pad edges to preserve length
        pad_left = window // 2
        pad_right = window - 1 - pad_left
        padded = np.pad(silence_mask.astype(float), (pad_left, pad_right), mode='edge')
        smoothed = np.convolve(padded, kernel, mode='valid')

        # Binary decision with hysteresis threshold
        smoothed_mask = smoothed > 0.5

        # Apply duration constraints post-smoothing
        return self._apply_duration_constraints(smoothed_mask)
    
    def _apply_duration_constraints(self, mask: np.ndarray) -> np.ndarray:
        """Enforce minimum duration for silence and speech segments"""
        result = mask.copy()
        
        min_silence_frames = int(self.min_silence_duration * self.sample_rate / self.frame_shift)
        min_speech_frames = int(self.min_speech_duration * self.sample_rate / self.frame_shift)
        
        # Find runs of silence and speech
        changes = np.diff(np.concatenate(([False], mask, [False])).astype(int))
        run_starts = np.where(changes == 1)[0]
        run_ends = np.where(changes == -1)[0]
        
        # Remove short silence segments
        for start, end in zip(run_starts, run_ends):
            if (end - start) < min_silence_frames:
                result[start:end] = False
        
        # Remove short speech segments (fill in brief gaps)
        changes = np.diff(np.concatenate(([True], ~result, [True])).astype(int))
        run_starts = np.where(changes == 1)[0]
        run_ends = np.where(changes == -1)[0]
        
        for start, end in zip(run_starts, run_ends):
            if (end - start) < min_speech_frames:
                result[start:end] = True
        
        return result
    
    def _frames_to_segments(self, silence_mask: np.ndarray, energy: np.ndarray, zcr: np.ndarray) -> List[SilenceSegment]:
        """Convert frame-level mask to time-based segments"""
        segments = []
        
        if len(silence_mask) == 0:
            return segments
        
        # Find silence runs
        changes = np.diff(np.concatenate(([False], silence_mask, [False])).astype(int))
        run_starts = np.where(changes == 1)[0]
        run_ends = np.where(changes == -1)[0]
        
        frame_time = self.frame_shift / self.sample_rate
        
        for start_frame, end_frame in zip(run_starts, run_ends):
            start_time = start_frame * frame_time
            end_time = end_frame * frame_time
            duration = end_time - start_time
            
            frame_slice = slice(start_frame, end_frame)
            segment_energy = energy[frame_slice]
            segment_zcr = zcr[frame_slice]

            energy_margin = self.energy_threshold - np.mean(segment_energy)
            energy_range = max(1e-6, self.energy_threshold - self.noise_floor_energy)
            energy_conf = np.clip(energy_margin / energy_range, 0.0, 1.0)

            zcr_margin = self.zcr_threshold - np.mean(segment_zcr)
            zcr_conf = np.clip(zcr_margin / max(self.zcr_threshold, 1e-6), 0.0, 1.0)

            duration_conf = np.clip(duration / self.min_silence_duration, 0.0, 1.0)
            confidence = float(np.clip(0.6 * energy_conf + 0.2 * zcr_conf + 0.2 * duration_conf, 0.0, 1.0))

            segments.append(SilenceSegment(
                start_time=start_time,
                end_time=end_time,
                confidence=confidence,
                duration=duration
            ))
        
        return segments
    
    def visualize_detection(self, audio_data: np.ndarray, segments: List[SilenceSegment], 
                          output_path: Optional[str] = None):
        """Create visualization of silence detection (optional)"""
        try:
            import matplotlib.pyplot as plt
            
            time_axis = np.linspace(0, len(audio_data) / self.sample_rate, len(audio_data))
            
            fig, axes = plt.subplots(3, 1, figsize=(12, 8))
            
            # Audio waveform
            axes[0].plot(time_axis, audio_data, alpha=0.7, color='blue')
            axes[0].set_title('Audio Waveform')
            axes[0].set_ylabel('Amplitude')
            
            # Mark silence segments
            for seg in segments:
                axes[0].axvspan(seg.start_time, seg.end_time, alpha=0.3, color='red', label='Silence')
            
            # Energy
            energy = self._calculate_energy(audio_data)
            frame_times = np.linspace(0, len(audio_data) / self.sample_rate, len(energy))
            axes[1].plot(frame_times, energy, color='green')
            axes[1].axhline(y=self.energy_threshold, color='red', linestyle='--', label='Threshold')
            axes[1].set_title('Short-time Energy (log scale)')
            axes[1].set_ylabel('Log Energy')
            axes[1].legend()
            
            # Zero-crossing rate
            zcr = self._calculate_zcr(audio_data)
            axes[2].plot(frame_times, zcr, color='orange')
            axes[2].axhline(y=self.zcr_threshold, color='red', linestyle='--', label='Threshold')
            axes[2].set_title('Zero-Crossing Rate')
            axes[2].set_ylabel('ZCR')
            axes[2].set_xlabel('Time (s)')
            axes[2].legend()
            
            plt.tight_layout()
            
            if output_path:
                plt.savefig(output_path, dpi=150, bbox_inches='tight')
                print(f"📊 Visualization saved to {output_path}")
            else:
                plt.show()
                
        except ImportError:
            print("📈 Matplotlib not available for visualization")