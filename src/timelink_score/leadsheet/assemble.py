"""리드시트 조립 — 멜로디 + 코드 + 조성 → music21 Stream."""

from __future__ import annotations

import logging
from typing import Any

from music21 import (
    expressions,
    key as m21key,
    meter,
    note as m21note,
    stream,
    tempo,
)

from ..chord.extract import ChordEvent
from ..key.analyze import KeyResult
from ..melody.extract import NoteEvent
from ..rights.attribution import build_metadata

logger = logging.getLogger(__name__)


class LeadSheetError(Exception):
    """리드시트 조립 실패."""


def assemble_leadsheet(
    *,
    melody,
    chords,
    key_result=None,
    bpm: float = 120.0,
    time_signature: str = "4/4",
    title: str = "",
    artist: str = "",
    rights=None,
    quantize_grid: str = "16th",
):
    """멜로디 + 코드 + 조성 → music21 Score."""
    if not melody:
        raise LeadSheetError("melody is empty")

    score = stream.Score()
    md = build_metadata(title=title, artist=artist, rights=rights)
    score.insert(0, md)

    part = stream.Part()

    if key_result is not None:
        k = _key_from_result(key_result)
    else:
        k = m21key.Key("C")
    part.insert(0, k)

    part.insert(0, meter.TimeSignature(time_signature))
    part.insert(0, tempo.MetronomeMark(number=float(bpm)))

    melody_sorted = sorted(melody, key=lambda e: e.start)

    prev_end = 0.0
    for ev in melody_sorted:
        if ev.start > prev_end + 0.01:
            r = m21note.Rest()
            ql = _sec_to_ql(ev.start - prev_end, bpm)
            if ql > 0:
                r.quarterLength = ql
                part.append(r)

        n = m21note.Note()
        n.pitch.midi = ev.midi
        ql = _sec_to_ql(ev.duration, bpm)
        if ql <= 0:
            ql = 0.25
        n.quarterLength = ql
        part.append(n)
        prev_end = ev.end

    _insert_chord_symbols(part, chords, bpm)

    score.insert(0, part)
    return score


def _insert_chord_symbols(part, chords, bpm):
    """코드 심볼을 음표 위 텍스트로 삽입."""
    notes = [n for n in part.recurse().notes if hasattr(n, "pitch")]
    if not notes:
        return

    last_note = None
    for ce in chords:
        try:
            target_offset = _sec_to_ql(ce.start, bpm)
        except Exception:
            continue

        target_note = None
        for n in notes:
            try:
                n_offset = n.getOffsetInHierarchy(part)
            except Exception:
                continue
            if n_offset >= target_offset - 0.01:
                target_note = n
                break

        if target_note is None or target_note is last_note:
            continue
        last_note = target_note

        try:
            txt = expressions.TextExpression(ce.symbol)
            target_note.expressions.append(txt)
        except Exception as e:
            logger.debug("chord text failed: %s (%s)", ce.symbol, e)


def _key_from_result(kr):
    mode = "major" if kr.mode == "major" else "minor"
    try:
        return m21key.Key(kr.tonic, mode)
    except Exception:
        return m21key.Key("C")


def _sec_to_ql(seconds: float, bpm: float) -> float:
    if bpm <= 0:
        bpm = 120.0
    ql = seconds * (bpm / 60.0)
    ql = round(ql * 4) / 4
    if ql < 0.25:
        ql = 0.25
    return ql


def _grid_divisors(grid: str):
    mapping = {
        "4th": [1], "8th": [2], "16th": [4], "32nd": [8],
        "triplet8th": [3], "triplet16th": [6],
    }
    return mapping.get(grid, [4])