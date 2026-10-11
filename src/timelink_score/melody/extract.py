"""멜로디 추출 — torchcrepe F0 추정.

torchcrepe: CREPE 모델의 PyTorch 구현체.
- TensorFlow 불필요 (DLL 문제 없음)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import librosa
import numpy as np

logger = logging.getLogger(__name__)


class MelodyExtractionError(Exception):
    """멜로디 추출 실패."""


@dataclass(frozen=True)
class NoteEvent:
    """단일 음표 이벤트."""
    start: float
    end: float
    midi: int
    freq: float
    confidence: float

    @property
    def duration(self) -> float:
        return self.end - self.start

    @property
    def note_name(self) -> str:
        names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        octave = self.midi // 12 - 1
        return f"{names[self.midi % 12]}{octave}"


def hz_to_midi(freq):
    """Hz → MIDI 노트 번호."""
    return 69 + 12 * np.log2(np.asarray(freq) / 440.0)


def extract_melody(
    audio_path,
    *,
    sr: int = 16000,
    hop_length: int = 160,
    confidence_threshold: float = 0.5,
    min_note_duration: float = 0.08,
    median_filter_size: int = 5,
    model_capacity: str = "full",
    device: str | None = None,
):
    """오디오에서 멜로디(단선율) 추출."""
    try:
        import torch
        import torchcrepe
    except ImportError as e:
        raise MelodyExtractionError(
            "torchcrepe가 설치되어 있지 않습니다. "
            "`pip install torchcrepe` 후 다시 시도하세요."
        ) from e

    audio_path = Path(audio_path)
    if not audio_path.exists():
        raise MelodyExtractionError(f"오디오 파일이 없습니다: {audio_path}")

    try:
        y, sr = librosa.load(str(audio_path), sr=sr, mono=True)
    except Exception as e:
        raise MelodyExtractionError(f"오디오 로드 실패: {e}") from e

    if len(y) == 0:
        raise MelodyExtractionError("빈 오디오입니다.")

    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"

    logger.info("torchcrepe 실행: %s (model=%s, device=%s)",
                audio_path.name, model_capacity, device)

    audio_t = torch.from_numpy(y).float().unsqueeze(0).to(device)

    try:
        with torch.no_grad():
            f0, confidence = torchcrepe.predict(
                audio_t,
                sample_rate=sr,
                hop_length=hop_length,
                fmin=50.0,
                fmax=1100.0,
                model=model_capacity,
                batch_size=512,
                device=device,
                return_periodicity=True,
            )
    except Exception as e:
        raise MelodyExtractionError(f"torchcrepe 추론 실패: {e}") from e

    f0 = f0.squeeze(0).cpu().numpy()
    confidence = confidence.squeeze(0).cpu().numpy()

    n_frames = len(f0)
    times = np.arange(n_frames) * (hop_length / sr)

    midi_arr = np.zeros_like(f0, dtype=float)
    valid = f0 > 0
    midi_arr[valid] = hz_to_midi(f0[valid])

    midi_arr[confidence < confidence_threshold] = np.nan
    midi_arr[~valid] = np.nan
    midi_arr = _interpolate_nans(midi_arr)

    midi_rounded = np.round(midi_arr).astype(int)

    if median_filter_size >= 3:
        from scipy.signal import medfilt
        midi_rounded = medfilt(midi_rounded, kernel_size=median_filter_size).astype(int)

    events = _frames_to_notes(
        times=times,
        midi=midi_rounded,
        freq=f0,
        conf=confidence,
        min_duration=min_note_duration,
    )

    logger.info("음표 %d개 추출", len(events))
    return events


def _interpolate_nans(arr):
    if not np.any(np.isnan(arr)):
        return arr
    nans = np.isnan(arr)
    if nans.all():
        return np.zeros_like(arr)
    idx = np.arange(len(arr))
    arr[nans] = np.interp(idx[nans], idx[~nans], arr[~nans])
    return arr


def _frames_to_notes(*, times, midi, freq, conf, min_duration):
    if len(midi) == 0:
        return []

    events = []
    cur_midi = int(midi[0])
    start_idx = 0

    for i in range(1, len(midi)):
        if int(midi[i]) != cur_midi:
            _append_note(events, times, midi, freq, conf, start_idx, i, min_duration)
            cur_midi = int(midi[i])
            start_idx = i

    _append_note(events, times, midi, freq, conf, start_idx, len(midi), min_duration)
    return events


def _append_note(events, times, midi, freq, conf, start_idx, end_idx, min_duration):
    if end_idx <= start_idx:
        return

    t_start = float(times[start_idx])
    t_end = float(times[end_idx - 1])
    duration = t_end - t_start

    if duration < min_duration:
        return

    seg_midi = midi[start_idx:end_idx]
    seg_freq = freq[start_idx:end_idx]
    seg_conf = conf[start_idx:end_idx]

    valid = seg_freq > 0
    mean_freq = float(np.mean(seg_freq[valid])) if valid.any() else 0.0

    events.append(
        NoteEvent(
            start=t_start,
            end=t_end,
            midi=int(np.median(seg_midi)),
            freq=mean_freq,
            confidence=float(np.mean(seg_conf)),
        )
    )


def format_melody(events, max_notes: int = 30):
    """멜로디를 문자열로 (디버그)."""
    parts = [f"{e.note_name}({e.duration:.2f}s)" for e in events[:max_notes]]
    suffix = f" ... (+{len(events) - max_notes})" if len(events) > max_notes else ""
    return " ".join(parts) + suffix
