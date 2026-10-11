"""TLNK 컨테이너 헤더 파서.

TLNK 레이아웃:
    [0..3]   "TLNK"                   magic 0x54 0x4C 0x4E 0x4B
    [4]      version = 0x03
    [5..8]   headerLen (uint32 BE)
    [9..]    header JSON (UTF-8)
    [세그먼트...]  ciphertext

본 모듈은 헤더(평문 JSON)만 파싱합니다. 세그먼트는 서버에서 복호화.
"""

from __future__ import annotations

import json
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any

TLNK_MAGIC = b"TLNK"
SUPPORTED_VERSIONS = {0x03}
HEADER_PREFIX_LEN = 9  # magic(4) + version(1) + headerLen(4)


class TL3ParseError(Exception):
    """TL3 헤더 파싱 실패."""


@dataclass(frozen=True)
class TL3Header:
    """TLNK 헤더 메타데이터."""

    version: int
    raw: dict[str, Any]

    @property
    def kind(self) -> str:
        return self.raw.get("kind", "")

    @property
    def title(self) -> str:
        return self.raw.get("title", "")

    @property
    def artist(self) -> str:
        return self.raw.get("artist", "")

    @property
    def bpm(self) -> int:
        return int(self.raw.get("bpm", 0))

    @property
    def dur_sec(self) -> int:
        return int(self.raw.get("dur_sec", 0))

    @property
    def sample_rate(self) -> int:
        return int(self.raw.get("fs", 0))

    @property
    def channels(self) -> int:
        return int(self.raw.get("ch", 0))

    @property
    def fid(self) -> str:
        return self.raw.get("fid", "")

    @property
    def num_segments(self) -> int:
        mp3 = self.raw.get("mp3") or {}
        return int(mp3.get("N", 0))

    @property
    def rights(self) -> dict[str, Any]:
        return self.raw.get("rights") or {}

    def assert_music(self) -> None:
        if self.kind != "music":
            raise TL3ParseError(
                f"이 파일은 음원이 아닙니다. kind='{self.kind}' (music 이어야 함)"
            )


def parse_header(path: str | Path) -> TL3Header:
    """TL3 파일의 헤더만 파싱 (세그먼트는 건드리지 않음)."""
    path = Path(path)
    if not path.exists():
        raise TL3ParseError(f"파일이 존재하지 않습니다: {path}")

    with path.open("rb") as f:
        prefix = f.read(HEADER_PREFIX_LEN)
        if len(prefix) < HEADER_PREFIX_LEN:
            raise TL3ParseError("파일이 너무 짧습니다 (헤더 prefix 부족).")

        magic = prefix[0:4]
        if magic != TLNK_MAGIC:
            raise TL3ParseError(
                f"TLNK magic 불일치: {magic!r} (기대값 {TLNK_MAGIC!r}). TL3 파일이 아닙니다."
            )

        version = prefix[4]
        if version not in SUPPORTED_VERSIONS:
            raise TL3ParseError(
                f"지원하지 않는 버전: 0x{version:02X} (지원: {sorted(SUPPORTED_VERSIONS)})"
            )

        (header_len,) = struct.unpack(">I", prefix[5:9])
        if header_len == 0 or header_len > 10 * 1024 * 1024:
            raise TL3ParseError(f"비정상적인 headerLen: {header_len}")

        header_bytes = f.read(header_len)
        if len(header_bytes) != header_len:
            raise TL3ParseError("헤더 JSON이 잘렸습니다.")

    try:
        raw = json.loads(header_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise TL3ParseError(f"헤더 JSON 파싱 실패: {e}") from e

    if not isinstance(raw, dict):
        raise TL3ParseError("헤더 JSON이 객체가 아닙니다.")

    return TL3Header(version=version, raw=raw)


def parse_header_bytes(data: bytes) -> TL3Header:
    """메모리 상의 TL3 바이트에서 헤더만 파싱."""
    if len(data) < HEADER_PREFIX_LEN:
        raise TL3ParseError("데이터가 너무 짧습니다.")

    magic = data[0:4]
    if magic != TLNK_MAGIC:
        raise TL3ParseError(f"TLNK magic 불일치: {magic!r}")

    version = data[4]
    if version not in SUPPORTED_VERSIONS:
        raise TL3ParseError(f"지원하지 않는 버전: 0x{version:02X}")

    (header_len,) = struct.unpack(">I", data[5:9])
    if header_len == 0 or 9 + header_len > len(data):
        raise TL3ParseError(f"headerLen 부정확: {header_len}")

    header_bytes = data[9 : 9 + header_len]
    try:
        raw = json.loads(header_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise TL3ParseError(f"헤더 JSON 파싱 실패: {e}") from e

    return TL3Header(version=version, raw=raw)
