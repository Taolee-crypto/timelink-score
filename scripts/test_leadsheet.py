"""리드시트 조립 + PDF 렌더링 테스트."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import numpy as np
import soundfile as sf

from timelink_score.chord.extract import extract_chords
from timelink_score.key.analyze import analyze_key
from timelink_score.leadsheet.assemble import assemble_leadsheet
from timelink_score.melody.extract import extract_melody
from timelink_score.score.render import render_pdf_from_score

SR = 16000


def note(freq, dur, sr=SR, amp=0.3):
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
    wave = amp * (np.sin(2 * np.pi * freq * t) +
                  0.3 * np.sin(2 * np.pi * 2 * freq * t))
    fade = int(sr * 0.02)
    wave[:fade] *= np.linspace(0, 1, fade)
    wave[-fade:] *= np.linspace(1, 0, fade)
    return wave.astype(np.float32)


def chord_audio(freqs, dur, sr=SR):
    return sum(note(f, dur, sr) for f in freqs) / len(freqs)


def main() -> int:
    melody_freqs = [261.63, 293.66, 329.63, 349.23, 392.00, 440.00, 493.88, 523.25]
    melody_audio = np.concatenate([note(f, 0.5) for f in melody_freqs])
    melody_audio = np.concatenate([melody_audio, melody_audio])

    chords_audio = np.concatenate([
        chord_audio([261.63, 329.63, 392.00], 2.0),
        chord_audio([220.00, 261.63, 329.63], 2.0),
        chord_audio([174.61, 220.00, 261.63], 2.0),
        chord_audio([196.00, 246.94, 293.66], 2.0),
    ])

    mixed = melody_audio + 0.5 * chords_audio

    tmp = Path("output") / "test_leadsheet.wav"
    tmp.parent.mkdir(exist_ok=True)
    sf.write(str(tmp), mixed, SR)

    print(f"오디오: {tmp} ({len(mixed) / SR:.2f}초)")
    print()

    print("[1/5] 멜로디 추출...")
    melody = extract_melody(tmp, sr=SR)
    print(f"      음표 {len(melody)}개")

    print("[2/5] 코드 추출...")
    chords = extract_chords(tmp, sr=SR)
    print(f"      코드 {len(chords)}개")

    print("[3/5] 조성 분석...")
    key_result = analyze_key(tmp, sr=SR)
    print(f"      {key_result.korean}")

    print("[4/5] 리드시트 조립...")
    score = assemble_leadsheet(
        melody=melody,
        chords=chords,
        key_result=key_result,
        bpm=120.0,
        time_signature="4/4",
        title="Test Lead Sheet",
        artist="Test Artist",
        rights={
            "creator_name": "Hong",
            "isrc": "KRTEST0000001",
            "copyright_year": 2026,
            "country": "KR",
        },
    )

    # DEBUG: 0-duration 객체 찾기
    print("  DEBUG: 0-duration 검색...")
    found = 0
    for el in score.recurse():
        try:
            d = getattr(el, 'duration', None)
            if d is not None and hasattr(d, 'quarterLength'):
                if d.quarterLength == 0:
                    print(f"    0-dur: {type(el).__name__} | {repr(el)[:100]}")
                    found += 1
        except Exception:
            pass
    print(f"  DEBUG: {found}개 발견")

    out_xml = Path("output") / "test_leadsheet.musicxml"
    score.write("musicxml", fp=str(out_xml))
    print(f"      MusicXML: {out_xml}")

    print("[5/5] PDF 렌더링 (LilyPond)...")
    out_pdf = Path("output") / "test_leadsheet.pdf"
    try:
        render_pdf_from_score(score, out_pdf)
        print(f"      PDF: {out_pdf}")
    except Exception as e:
        print(f"      PDF 렌더링 실패: {e}")
        return 1

    print()
    print("완료!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())