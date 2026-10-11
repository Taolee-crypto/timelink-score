"""코드 추출 테스트 — 합성 오디오 (C-Am-F-G)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import numpy as np
import soundfile as sf

from timelink_score.chord.extract import extract_chords, format_progression


SR = 22050


def note(freq, dur, sr=SR, amp=0.3):
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
    return amp * np.sin(2 * np.pi * freq * t).astype(np.float32)


def chord_audio(freqs, dur, sr=SR):
    return sum(note(f, dur, sr) for f in freqs) / len(freqs)


def main():
    # C-Am-F-G (각 2초)
    audio = np.concatenate([
        chord_audio([261.63, 329.63, 392.00], 2.0),  # C
        chord_audio([220.00, 261.63, 329.63], 2.0),  # Am
        chord_audio([174.61, 220.00, 261.63], 2.0),  # F
        chord_audio([196.00, 246.94, 293.66], 2.0),  # G
    ])

    # 임시 WAV 저장 (madmom은 파일 입력 필요)
    tmp = Path("output") / "test_chord.wav"
    tmp.parent.mkdir(exist_ok=True)
    sf.write(str(tmp), audio, SR)

    print(f"오디오: {tmp} ({len(audio) / SR:.2f}초)")
    print("기대: C → Am → F → G")
    print()

    events = extract_chords(tmp)

    print(f"{'시작':>6} {'종료':>6} {'라벨':>12} {'심볼':>8}")
    print("-" * 40)
    for e in events:
        print(f"{e.start:>6.2f} {e.end:>6.2f} {e.label:>12} {e.symbol:>8}")

    print()
    print(f"진행: {format_progression(events)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
