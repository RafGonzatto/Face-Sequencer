#!/usr/bin/env python3
"""Debug do pipeline ElevenLabs com thresholds adaptativos e scoring de confiança."""

from __future__ import annotations

import librosa
import numpy as np

from audio_aligner import AudioAligner
from enhanced_silence_detector import EnhancedSilenceDetector


def _summarize_segments(label: str, segments, total_duration: float) -> None:
    print(f"   ▸ {label}: {len(segments)} segmentos")
    if not segments:
        return

    durations = np.array([seg.duration for seg in segments])
    confidences = np.array([seg.confidence for seg in segments])
    coverage = durations.sum() / total_duration if total_duration else 0.0

    print(f"     • Cobertura de silêncio: {coverage * 100:.1f}%")
    print(f"     • Duração média: {durations.mean():.3f}s | mediana: {np.median(durations):.3f}s")
    print(
        "     • Confiança média: "
        f"{confidences.mean():.3f} | mínimo: {confidences.min():.3f} | máximo: {confidences.max():.3f}"
    )


def _analyze_variant(label: str, audio: np.ndarray, sample_rate: int, detector: EnhancedSilenceDetector):
    print(f"\n� {label} ({len(audio)/sample_rate:.2f}s)")

    rms = np.sqrt(np.mean(audio**2))
    print(f"   • RMS bruto: {rms:.6f}")

    normalized_audio = detector._normalize_audio(audio)  # uso interno para depuração
    normalized_rms = np.sqrt(np.mean(normalized_audio**2))
    print(f"   • RMS normalizado: {normalized_rms:.6f}")

    energy = detector._calculate_energy(normalized_audio)
    zcr = detector._calculate_zcr(normalized_audio)

    segments = detector.detect_silence_segments(audio, adaptive_thresholds=True)

    print(
        "   • Threshold energia: "
        f"{detector.energy_threshold:.4f} | piso: {detector.noise_floor_energy:.4f} | teto: {detector.energy_ceiling:.4f}"
    )
    print(f"   • Threshold ZCR: {detector.zcr_threshold:.4f}")
    print(f"   • Energia (log) min/med/max: {energy.min():.4f} | {np.median(energy):.4f} | {energy.max():.4f}")
    print(f"   • ZCR min/med/max: {zcr.min():.4f} | {np.median(zcr):.4f} | {zcr.max():.4f}")

    _summarize_segments("Silêncio", segments, len(audio) / sample_rate)

    return {
        "segments": segments,
        "energy": energy,
        "zcr": zcr,
        "normalized_audio": normalized_audio,
    }


def debug_elevenlabs_processing(audio_file: str = "test_audio.mp3"):
    """Executa análise comparativa entre áudio bruto e processado pelo aligner."""

    print("🔬 Debug específico do processamento ElevenLabs...")

    raw_audio, sample_rate = librosa.load(audio_file, sr=16000)
    raw_detector = EnhancedSilenceDetector(sample_rate=sample_rate)
    raw_result = _analyze_variant("1. Áudio RAW", raw_audio, sample_rate, raw_detector)

    aligner = AudioAligner()
    processed_audio, processed_sr = aligner.preprocess_audio(audio_file)
    processed_detector = EnhancedSilenceDetector(sample_rate=processed_sr)
    processed_result = _analyze_variant("2. Áudio Processado", processed_audio, processed_sr, processed_detector)

    print("\n📊 Resumo comparativo:")
    print(f"   • Silêncios RAW: {len(raw_result['segments'])}")
    print(f"   • Silêncios Processado: {len(processed_result['segments'])}")

    raw_conf = [seg.confidence for seg in raw_result['segments']]
    proc_conf = [seg.confidence for seg in processed_result['segments']]

    if raw_conf:
        print(f"   • Confiança média RAW: {np.mean(raw_conf):.3f}")
    if proc_conf:
        print(f"   • Confiança média Processado: {np.mean(proc_conf):.3f}")

    print(
        "   • Threshold energia RAW/Processado: "
        f"{raw_detector.energy_threshold:.4f} / {processed_detector.energy_threshold:.4f}"
    )
    print(
        "   • Threshold ZCR RAW/Processado: "
        f"{raw_detector.zcr_threshold:.4f} / {processed_detector.zcr_threshold:.4f}"
    )

    return {
        "raw": raw_result,
        "processed": processed_result,
    }


if __name__ == "__main__":
    debug_elevenlabs_processing()

if __name__ == "__main__":
    debug_elevenlabs_processing()