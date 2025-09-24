import numpy as np
from enhanced_silence_detector import EnhancedSilenceDetector


def test_detect_silence_basic_short_signal():
    det = EnhancedSilenceDetector(sample_rate=16000)
    # 0.3s of silence, 0.3s of tone, 0.3s of silence
    sr = det.sample_rate
    t_sil = np.zeros(int(0.3 * sr))
    t_tone = 0.05 * np.sin(2 * np.pi * 440 * np.linspace(0, 0.3, int(0.3 * sr), endpoint=False))
    audio = np.concatenate([t_sil, t_tone, t_sil])
    segments = det.detect_silence_segments(audio)
    # Expect at least 2 silence segments (start and end)
    assert len(segments) >= 2
    # First segment should start near 0
    assert segments[0].start_time < 0.05


def test_adaptive_thresholds_stable():
    det = EnhancedSilenceDetector(sample_rate=16000)
    sr = det.sample_rate
    # Generate low energy noise + higher energy tone
    noise = 0.005 * np.random.randn(int(0.5 * sr))
    tone = 0.05 * np.sin(2 * np.pi * 220 * np.linspace(0, 0.5, int(0.5 * sr), endpoint=False))
    audio = np.concatenate([noise, tone])
    _ = det.detect_silence_segments(audio)
    # Energy threshold should sit between noise and tone RMS (log domain)
    assert det.noise_floor_energy < det.energy_threshold < det.energy_ceiling
