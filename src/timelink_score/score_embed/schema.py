"""악보 데이터 스키마 — TL3 헤더에 임베드되는 경량 데이터.

압축 후 ~5KB. TL3 헤더 JSON의 "score" 필드에 들어감.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# 현재 알고리즘 버전 (변경 시 마이그레이션)
SCORE_SCHEMA_VERSION = 1


@dataclass
class NoteData:
    """음표 (경량)."""

    s: float          # start (초)
    d: float          # duration (초)
    m: int            # midi
    conf: float = 0.0  # confidence

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"s": round(self.s, 4), "d": round(self.d, 4), "m": self.m}
        if self.conf:
            d["conf"] = round(self.conf, 3)
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "NoteData":
        return cls(s=d["s"], d=d["d"], m=d["m"], conf=d.get("conf", 0.0))


@dataclass
class ChordData:
    """코드 (경량)."""

    s: float          # start (초)
    e: float          # end (초)
    sym: str          # symbol (예: "C", "Am")
    conf: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"s": round(self.s, 4), "e": round(self.e, 4), "sym": self.sym}
        if self.conf:
            d["conf"] = round(self.conf, 3)
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ChordData":
        return cls(s=d["s"], e=d["e"], sym=d["sym"], conf=d.get("conf", 0.0))


@dataclass
class LyricData:
    """가사 (경량)."""

    s: float          # start (초)
    text: str         # 음절
    m: int | None = None  # 연결된 midi (선택)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"s": round(self.s, 4), "text": self.text}
        if self.m is not None:
            d["m"] = self.m
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "LyricData":
        return cls(s=d["s"], text=d["text"], m=d.get("m"))


@dataclass
class KeyData:
    """조성."""

    tonic: str              # "C", "F#", "Bb"
    mode: str               # "major" | "minor"
    sharps_flats: int = 0   # 양수=샵, 음수=플랫
    conf: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "tonic": self.tonic,
            "mode": self.mode,
            "sharps_flats": self.sharps_flats,
        }
        if self.conf:
            d["conf"] = round(self.conf, 3)
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "KeyData":
        return cls(
            tonic=d["tonic"],
            mode=d["mode"],
            sharps_flats=d.get("sharps_flats", 0),
            conf=d.get("conf", 0.0),
        )


@dataclass
class ScoreData:
    """TL3 헤더에 임베드되는 악보 데이터 전체."""

    version: int = SCORE_SCHEMA_VERSION
    generated_at: str = ""
    algorithm: str = "timelink-score-v0.1"

    key: KeyData | None = None
    time_signature: str = "4/4"
    bpm: float = 120.0

    melody: list[NoteData] = field(default_factory=list)
    chords: list[ChordData] = field(default_factory=list)
    lyrics: list[LyricData] = field(default_factory=list)

    # 무결성
    score_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "version": self.version,
            "generated_at": self.generated_at,
            "algorithm": self.algorithm,
            "time_signature": self.time_signature,
            "bpm": self.bpm,
        }
        if self.key:
            d["key"] = self.key.to_dict()
        if self.melody:
            d["melody"] = [n.to_dict() for n in self.melody]
        if self.chords:
            d["chords"] = [c.to_dict() for c in self.chords]
        if self.lyrics:
            d["lyrics"] = [l.to_dict() for l in self.lyrics]
        if self.score_hash:
            d["score_hash"] = self.score_hash
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ScoreData":
        return cls(
            version=d.get("version", 1),
            generated_at=d.get("generated_at", ""),
            algorithm=d.get("algorithm", ""),
            key=KeyData.from_dict(d["key"]) if d.get("key") else None,
            time_signature=d.get("time_signature", "4/4"),
            bpm=float(d.get("bpm", 120.0)),
            melody=[NoteData.from_dict(n) for n in d.get("melody", [])],
            chords=[ChordData.from_dict(c) for c in d.get("chords", [])],
            lyrics=[LyricData.from_dict(l) for l in d.get("lyrics", [])],
            score_hash=d.get("score_hash", ""),
        )

    def is_empty(self) -> bool:
        return not self.melody and not self.chords