"""TL3 헤더에 악보 데이터 삽입/추출 테스트."""

import sys
from pathlib import Path

sys.path.insert(0, "src")

from timelink_score.score_embed import (
    ScoreData, NoteData, ChordData, KeyData,
    embed_score_in_tl3, extract_score_from_tl3,
)

# 1. 테스트용 TL3 생성 (기존 샘플 사용)
src_tl3 = Path("tests/fixtures/sample_minimal.tl3")
if not src_tl3.exists():
    print(f"샘플 TL3 없음: {src_tl3}")
    sys.exit(1)

print(f"원본 TL3: {src_tl3} ({src_tl3.stat().st_size} bytes)")

# 2. ScoreData 생성
score = ScoreData(
    generated_at="2026-10-12T12:00:00Z",
    key=KeyData("C", "major", 0, 0.9),
    time_signature="4/4",
    bpm=120.0,
    melody=[
        NoteData(0.0, 0.5, 60, 0.9),
        NoteData(0.5, 0.5, 62, 0.9),
        NoteData(1.0, 0.5, 64, 0.9),
        NoteData(1.5, 0.5, 65, 0.9),
        NoteData(2.0, 0.5, 67, 0.9),
    ],
    chords=[
        ChordData(0.0, 2.0, "C", 0.9),
        ChordData(2.0, 4.0, "G", 0.9),
    ],
)

# 3. TL3에 삽입
out_tl3 = Path("output/test_with_score.tl3")
out_tl3.parent.mkdir(exist_ok=True)

embed_score_in_tl3(src_tl3, score, out_path=out_tl3)
print(f"악보 삽입 후: {out_tl3} ({out_tl3.stat().st_size} bytes)")
print(f"증가: {out_tl3.stat().st_size - src_tl3.stat().st_size} bytes")

# 4. 다시 추출
restored = extract_score_from_tl3(out_tl3)
if restored is None:
    print("FAIL: score 추출 실패")
    sys.exit(1)

print(f"복원 성공")
print(f"  key: {restored.key.tonic} {restored.key.mode}")
print(f"  bpm: {restored.bpm}")
print(f"  멜로디: {len(restored.melody)}개")
print(f"  코드: {len(restored.chords)}개")
print(f"  첫 음: {restored.melody[0].m} (MIDI)")

# 5. 원본 비교
assert restored.bpm == score.bpm
assert len(restored.melody) == len(score.melody)
assert len(restored.chords) == len(score.chords)
assert restored.key.tonic == score.key.tonic
print("검증 OK")