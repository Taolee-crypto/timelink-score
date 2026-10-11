"""멜로디 추출 테스트 — 합성 멜로디 (도레미파솔라시도)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import numpy as np
import soundfile as sf

from timelink_score.melody.extract import extract_melody, format_melody


SR = 16000


def note(freq: float, dur: float, sr: int = SR, amp: float = 0.3) -> np.ndarray:
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
    wave = amp * (np.sin(2 * np.pi * freq * t) +
                  0.3 * np.sin(2 * np.pi * 2 * freq * t) +
                  0.1 * np.sin(2 * np.pi * 3 * freq * t))
    fade = int(sr * 0.02)
    wave[:fade] *= np.linspace(0, 1, fade)
    wave[-fade:] *= np.linspace(1, 0, fade)
    return wave.astype(np.float32)


def main() -> int:
    freqs = [261.63, 293.66, 329.63, 349.23, 392.00, 440.00, 493.88, 523.25]
    audio = np.concatenate([note(f, 0.5) for f in freqs])

    tmp = Path("output") / "test_melody.wav"
    tmp.parent.mkdir(exist_ok=True)
    sf.write(str(tmp), audio, SR)

    print(f"오디오: {tmp} ({len(audio) / SR:.2f}초)")
    print("기대: C4 D4 E4 F4 G4 A4 B4 C5")
    print()

    events = extract_melody(tmp, sr=SR)

    print(f"{'시작':>6} {'종료':>6} {'음':>6} {'MIDI':>5} {'Hz':>8} {'신뢰도':>8}")
    print("-" * 50)
    for e in events:
        print(
            f"{e.start:>6.2f} {e.end:>6.2f} {e.note_name:>6} "
            f"{e.midi:>5} {e.freq:>8.1f} {e.confidence:>8.3f}"
        )

    print()
    print(f"멜로디: {format_melody(events)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
