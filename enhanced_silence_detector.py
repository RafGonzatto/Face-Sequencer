# enhanced_silence_detector.py - Advanced Voice Activity Detection
"""
Enhanced silence detection using energy and zero-crossing rate analysis.
Replaces basic amplitude threshold with robust multi-feature VAD.
"""

import numpy as np
from scipy.signal import butter, lfilter
from typing import List, Tuple, Optional
from dataclasses import dataclass

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
    
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self.frame_length = int(0.025 * sample_rate)  # 25ms frames
        self.frame_shift = int(0.010 * sample_rate)   # 10ms shift (overlap for smoothness)
        
        # Adaptive thresholds (will be computed from audio stats)
        self.energy_threshold = 0.01
        self.zcr_threshold = 0.1
        
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
        
        # Calculate acoustic features
        energy = self._calculate_energy(audio_data)
        zcr = self._calculate_zcr(audio_data)
        
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
        silence_segments = self._frames_to_segments(smoothed_mask)
        
        print(f"✅ Detected {len(silence_segments)} silence segments")
        return silence_segments
    
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
        low_energy_percentile = np.percentile(energy, 15)  # Bottom 15% (more sensitive)
        high_energy_percentile = np.percentile(energy, 70)  # Top 70%
        
        # Threshold at 25% between low and high energy (more sensitive to silence)
        threshold = low_energy_percentile + 0.25 * (high_energy_percentile - low_energy_percentile)
        
        return max(threshold, -5.0)  # Lower minimum threshold for better silence detection
    
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
        
        # Median filtering for noise reduction
        from scipy.ndimage import median_filter
        smoothed = median_filter(silence_mask.astype(float), size=self.smoothing_window)
        
        # Convert back to binary with hysteresis
        smoothed_mask = smoothed > 0.5
        
        # Apply minimum duration constraints
        smoothed_mask = self._apply_duration_constraints(smoothed_mask)
        
        return smoothed_mask
    
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
    
    def _frames_to_segments(self, silence_mask: np.ndarray) -> List[SilenceSegment]:
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
            
            # Calculate confidence based on segment length and consistency
            confidence = min(1.0, duration / 0.2)  # Full confidence for 200ms+ segments
            
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