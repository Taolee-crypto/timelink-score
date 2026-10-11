"""조성 분석 — Krumhansl-Schmuckler 프로파일.

장조/단조 판별 및 조표(샵/플랫 개수) 산출.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import librosa
import numpy as np

NOTES_SHARP = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
NOTES_FLAT = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]

MAJOR_PROFILE = np.array(
    [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
)
MINOR_PROFILE = np.array(
    [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]
)

KEY_SIGNATURES: dict[tuple[str, str], int] = {
    ("C", "major"): 0,  ("G", "major"): 1,  ("D", "major"): 2,
    ("A", "major"): 3,  ("E", "major"): 4,  ("B", "major"): 5,
    ("F#", "major"): 6, ("C#", "major"): 7,
    ("F", "major"): -1, ("Bb", "major"): -2, ("Eb", "major"): -3,
    ("Ab", "major"): -4, ("Db", "major"): -5, ("Gb", "major"): -6,
    ("Cb", "major"): -7,
    ("A", "minor"): 0,  ("E", "minor"): 1,  ("B", "minor"): 2,
    ("F#", "minor"): 3, ("C#", "minor"): 4, ("G#", "minor"): 5,
    ("D#", "minor"): 6, ("A#", "minor"): 7,
    ("D", "minor"): -1, ("G", "minor"): -2, ("C", "minor"): -3,
    ("F", "minor"): -4, ("Bb", "minor"): -5, ("Eb", "minor"): -6,
    ("Ab", "minor"): -7,
}


@dataclass(frozen=True)
class KeyResult:
    """조성 분석 결과."""

    tonic: str
    mode: str
    confidence: float
    sharps_flats: int
    all_scores: dict[str, float]

    @property
    def name(self) -> str:
        return f"{self.tonic} {self.mode}"

    @property
    def korean(self) -> str:
        mode_kr = "장조" if self.mode == "major" else "단조"
        return f"{self.tonic} {mode_kr}"

    @property
    def signature_str(self) -> str:
        if self.sharps_flats == 0:
            return "조표 없음"
        if self.sharps_flats > 0:
            return f"샵 {self.sharps_flats}개"
        return f"플랫 {-self.sharps_flats}개"


def analyze_key(audio_path: str | Path, *, sr: int = 22050) -> KeyResult:
    """오디오 파일에서 조성을 분석."""
    audio_path = Path(audio_path)
    if not audio_path.exists():
        raise FileNotFoundError(f"오디오 파일이 없습니다: {audio_path}")

    y, sr = librosa.load(str(audio_path), sr=sr, mono=True)
    return analyze_key_from_array(y, sr=sr)


def analyze_key_from_array(
    y: np.ndarray, *, sr: int = 22050
) -> KeyResult:
    """numpy 오디오 배열에서 조성을 분석."""
    if y.ndim != 1:
        raise ValueError(f"mono 1D 배열이어야 합니다. shape={y.shape}")

    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    chroma_mean = chroma.mean(axis=1)

    scores: dict[str, float] = {}
    for i, note in enumerate(NOTES_SHARP):
        maj_rot = np.roll(MAJOR_PROFILE, i)
        min_rot = np.roll(MINOR_PROFILE, i)
        maj_corr = _safe_corr(chroma_mean, maj_rot)
        min_corr = _safe_corr(chroma_mean, min_rot)
        scores[f"{note} major"] = maj_corr
        scores[f"{note} minor"] = min_corr

    best_name = max(scores, key=scores.get)
    tonic, mode = best_name.split(" ")
    confidence = scores[best_name]

    sf_count = KEY_SIGNATURES.get((tonic, mode), 0)

    return KeyResult(
        tonic=tonic,
        mode=mode,
        confidence=float(confidence),
        sharps_flats=sf_count,
        all_scores=scores,
    )


def _safe_corr(a: np.ndarray, b: np.ndarray) -> float:
    if a.std() == 0 or b.std() == 0:
        return 0.0
    return float(np.corrcoef(a, b)[0, 1])
