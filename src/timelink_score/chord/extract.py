"""코드 추출 — librosa 크로마 + 템플릿 매칭.

컴파일 불필요. 순수 numpy/scipy/librosa.
기타리스트/가수용 리드시트에 필요한 코드 진행을 추출.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import librosa
import numpy as np
from scipy.signal import medfilt

from .templates import PITCH_CLASSES, SYMBOLS, TEMPLATES

logger = logging.getLogger(__name__)


class ChordExtractionError(Exception):
    """코드 추출 실패."""


@dataclass(frozen=True)
class ChordEvent:
    """시간 구간별 코드."""

    start: float
    end: float
    label: str      # 예: "C:maj"
    symbol: str     # 예: "C"

    @property
    def duration(self) -> float:
        return self.end - self.start


def _build_template_matrix() -> tuple[np.ndarray, list[tuple[str, str]]]:
    """모든 코드 후보의 정규화된 템플릿 행렬 생성.

    Returns:
        (templates, labels)
        templates: (M, 12) 정규화된 템플릿
        labels: [(root_name, quality), ...] 길이 M
    """
    rows: list[np.ndarray] = []
    labels: list[tuple[str, str]] = []

    for root_idx, root_name in enumerate(PITCH_CLASSES):
        for quality, profile in TEMPLATES.items():
            vec = np.roll(np.array(profile, dtype=np.float32), root_idx)
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm
            rows.append(vec)
            labels.append((root_name, quality))

    return np.stack(rows), labels


# 모듈 로드 시 한 번만 계산
_TEMPLATES, _LABELS = _build_template_matrix()


def extract_chords(
    audio_path: str | Path,
    *,
    sr: int = 22050,
    hop_length: int = 512,
    median_filter_size: int = 15,
    min_duration: float = 0.25,
) -> list[ChordEvent]:
    """오디오 파일에서 코드 진행을 추출.

    Args:
        audio_path: 입력 오디오 (wav/mp3).
        sr: 샘플레이트.
        hop_length: STFT hop.
        median_filter_size: 시간축 스무딩 커널 (홀수). 클수록 코드 변경 둔감.
        min_duration: 최소 코드 지속시간(초). 짧은 건 병합.

    Returns:
        ChordEvent 리스트.
    """
    audio_path = Path(audio_path)
    if not audio_path.exists():
        raise ChordExtractionError(f"오디오 파일이 없습니다: {audio_path}")

    try:
        y, sr = librosa.load(str(audio_path), sr=sr, mono=True)
    except Exception as e:
        raise ChordExtractionError(f"오디오 로드 실패: {e}") from e

    if len(y) == 0:
        raise ChordExtractionError("빈 오디오입니다.")

    # 1. 크로마 추출 (12차원 × T)
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=hop_length)

    # 프레임별 L2 정규화
    norms = np.linalg.norm(chroma, axis=0, keepdims=True)
    norms[norms == 0] = 1.0
    chroma = chroma / norms

    # 2. 템플릿 매칭 (코사인 유사도)
    scores = _TEMPLATES @ chroma  # (M, T)

    # 3. 프레임별 최고 점수 인덱스
    best_idx = np.argmax(scores, axis=0)  # (T,)

    # 4. 시간축 median filter (급격한 변경 억제)
    if median_filter_size >= 3:
        best_idx = medfilt(best_idx, kernel_size=median_filter_size).astype(int)

    # 5. 프레임 → 시간 → 세그먼트 병합
    times = librosa.frames_to_time(
        np.arange(len(best_idx)), sr=sr, hop_length=hop_length
    )
    duration = len(y) / sr

    events = _frames_to_events(
        times=times,
        best_idx=best_idx,
        duration=duration,
        min_duration=min_duration,
    )

    logger.info("코드 %d개 추출: %s", len(events), audio_path.name)
    return events


def _frames_to_events(
    *,
    times: np.ndarray,
    best_idx: np.ndarray,
    duration: float,
    min_duration: float,
) -> list[ChordEvent]:
    """프레임별 코드 인덱스 → 시간 구간 이벤트."""
    if len(best_idx) == 0:
        return []

    raw: list[tuple[float, float, int]] = []
    cur = int(best_idx[0])
    start = 0.0

    for i in range(1, len(best_idx)):
        idx = int(best_idx[i])
        if idx != cur:
            raw.append((start, float(times[i]), cur))
            cur = idx
            start = float(times[i])

    raw.append((start, duration, cur))

    # 최소 길이 병합 (짧은 세그먼트를 이전에 흡수)
    merged: list[tuple[float, float, int]] = []
    for s, e, idx in raw:
        if merged and (e - s) < min_duration:
            ps, _, pidx = merged[-1]
            merged[-1] = (ps, e, pidx)
        else:
            merged.append((s, e, idx))

    events: list[ChordEvent] = []
    for s, e, idx in merged:
        root_name, quality = _LABELS[idx]
        events.append(
            ChordEvent(
                start=s,
                end=e,
                label=f"{root_name}:{quality}",
                symbol=f"{root_name}{SYMBOLS.get(quality, quality)}",
            )
        )
    return events


def format_progression(events: list[ChordEvent]) -> str:
    """코드 진행을 문자열로."""
    return " | ".join(e.symbol for e in events)
