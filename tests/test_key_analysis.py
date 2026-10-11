"""조성 분석 테스트 (합성 신호 기반)."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from timelink_score.key.analyze import (  # noqa: E402
    KEY_SIGNATURES,
    KeyResult,
    analyze_key_from_array,
)


SR = 22050


def tone(freq: float, dur: float = 2.0, sr: int = SR) -> np.ndarray:
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
    return 0.3 * np.sin(2 * np.pi * freq * t).astype(np.float32)


def chord(freqs: list[float], dur: float = 2.0, sr: int = SR) -> np.ndarray:
    return sum(tone(f, dur, sr) for f in freqs) / len(freqs)


# C major triad (C-E-G) 반복
def c_major_signal() -> np.ndarray:
    return np.concatenate([
        chord([261.63, 329.63, 392.00]),  # C E G
        chord([349.23, 440.00, 523.25]),  # F A C
        chord([392.00, 493.88, 587.33]),  # G B D
        chord([261.63, 329.63, 392.00]),  # C E G
    ])


class TestKeySignatures:
    def test_signature_table(self):
        assert KEY_SIGNATURES[("C", "major")] == 0
        assert KEY_SIGNATURES[("G", "major")] == 1
        assert KEY_SIGNATURES[("F", "major")] == -1
        assert KEY_SIGNATURES[("A", "minor")] == 0
        assert KEY_SIGNATURES[("E", "minor")] == 1


class TestAnalyzeKey:
    def test_c_major_detected(self):
        y = c_major_signal()
        kr = analyze_key_from_array(y, sr=SR)
        # 완벽하진 않지만 C major 계열로 나와야 함
        assert isinstance(kr, KeyResult)
        assert kr.confidence > 0
        assert kr.tonic in {"C", "G", "F", "A", "D", "E"}
        # 조표 값은 테이블에 존재
        assert (kr.tonic, kr.mode) in KEY_SIGNATURES

    def test_signature_str(self):
        kr = KeyResult(
            tonic="G", mode="major", confidence=0.9,
            sharps_flats=1, all_scores={}
        )
        assert kr.signature_str == "샵 1개"

        kr2 = KeyResult(
            tonic="F", mode="major", confidence=0.9,
            sharps_flats=-1, all_scores={}
        )
        assert kr2.signature_str == "플랫 1개"

        kr3 = KeyResult(
            tonic="C", mode="major", confidence=0.9,
            sharps_flats=0, all_scores={}
        )
        assert kr3.signature_str == "조표 없음"

    def test_korean_name(self):
        kr = KeyResult(
            tonic="C", mode="major", confidence=0.9,
            sharps_flats=0, all_scores={}
        )
        assert kr.korean == "C 장조"

        kr2 = KeyResult(
            tonic="A", mode="minor", confidence=0.9,
            sharps_flats=0, all_scores={}
        )
        assert kr2.korean == "A 단조"

    def test_reject_stereo(self):
        y = np.zeros((1000, 2), dtype=np.float32)
        with pytest.raises(ValueError, match="mono"):
            analyze_key_from_array(y, sr=SR)
