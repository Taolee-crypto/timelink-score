"""MIDI → MusicXML 악보 생성.

- 조성(장조/단조) 및 조표 자동 반영
- 템포 반영
- 저작권자 정보 삽입 (원칙 6)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from music21 import converter, key, metadata, meter, stream, tempo

from ..key.analyze import KeyResult
from ..rights.attribution import build_metadata

logger = logging.getLogger(__name__)


class ScoreBuildError(Exception):
    """악보 생성 실패."""


def build_score(
    midi_path: str | Path,
    out_musicxml: str | Path,
    *,
    key_result: KeyResult | None = None,
    bpm: int | None = None,
    time_signature: str = "4/4",
    title: str = "",
    artist: str = "",
    rights: dict[str, Any] | None = None,
    quantize: bool = True,
    quantize_grid: str = "16th",
) -> Path:
    """MIDI를 MusicXML 악보로 변환."""
    midi_path = Path(midi_path)
    if not midi_path.exists():
        raise ScoreBuildError(f"MIDI 파일이 없습니다: {midi_path}")

    try:
        score = converter.parse(str(midi_path))
    except Exception as e:
        raise ScoreBuildError(f"MIDI 파싱 실패: {e}") from e

    flat = score.flatten()

    if quantize:
        try:
            flat.quantize(
                quarterLengthDivisors=_grid_divisors(quantize_grid),
                processOffsets=True,
                processDurations=True,
                recurse=True,
            )
        except Exception as e:
            logger.warning("양자화 실패, 원본 유지: %s", e)

    out = stream.Score()

    md = build_metadata(title=title, artist=artist, rights=rights)
    out.insert(0, md)

    part = stream.Part()

    if key_result is not None:
        k = _key_from_result(key_result)
    else:
        try:
            k = flat.analyze("key")
        except Exception:
            k = key.Key("C")
    part.insert(0, k)

    ts = meter.TimeSignature(time_signature)
    part.insert(0, ts)

    if bpm is None:
        try:
            bpm = int(flat.metronomeMarkBoundaries()[0][2].number)
        except Exception:
            bpm = 120
    part.insert(0, tempo.MetronomeMark(number=bpm))

    for n in flat.notes:
        part.append(n)

    out.insert(0, part)

    out_musicxml = Path(out_musicxml)
    out_musicxml.parent.mkdir(parents=True, exist_ok=True)
    try:
        out.write("musicxml", fp=str(out_musicxml))
    except Exception as e:
        raise ScoreBuildError(f"MusicXML 저장 실패: {e}") from e

    logger.info("MusicXML 생성: %s", out_musicxml)
    return out_musicxml


def _key_from_result(kr: KeyResult) -> key.Key:
    mode = "major" if kr.mode == "major" else "minor"
    try:
        return key.Key(kr.tonic, mode)
    except Exception:
        return key.Key("C")


def _grid_divisors(grid: str) -> list[int]:
    mapping = {
        "4th": [1],
        "8th": [2],
        "16th": [4],
        "32nd": [8],
        "triplet8th": [3],
        "triplet16th": [6],
    }
    return mapping.get(grid, [4])
