"""TLNK 헤더 파서 테스트."""

from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from timelink_score.tl3.header_parser import (  # noqa: E402
    TL3ParseError,
    parse_header,
    parse_header_bytes,
)


def make_tl3_bytes(header: dict, segments: list[bytes] | None = None) -> bytes:
    """테스트용 TLNK 바이트 생성."""
    header_json = json.dumps(header, ensure_ascii=False).encode("utf-8")
    out = b"TLNK" + bytes([0x03]) + struct.pack(">I", len(header_json)) + header_json
    if segments:
        for seg in segments:
            out += seg
    return out


SAMPLE_HEADER = {
    "v": 3,
    "aead": "AES-256-GCM",
    "kdf": "HKDF-SHA-256",
    "kind": "music",
    "title": "테스트 곡",
    "artist": "테스트 아티스트",
    "bpm": 120,
    "dur_sec": 3,
    "fs": 44100,
    "ch": 2,
    "mp3": {"N": 3, "seg_bytes": 176400, "last_bytes": 12345, "first_offset": 245},
    "fid": "test-fid-001",
    "rights": {
        "creator_id": 12345,
        "creator_name": "홍길동",
        "creator_wallet": "EQ...",
        "license_type": "exclusive",
        "isrc": "KRTEST0000001",
        "copyright_year": 2026,
        "country": "KR",
        "rights_confirmed": True,
    },
}


class TestParseHeaderBytes:
    def test_valid_header(self):
        data = make_tl3_bytes(SAMPLE_HEADER)
        h = parse_header_bytes(data)
        assert h.version == 0x03
        assert h.kind == "music"
        assert h.title == "테스트 곡"
        assert h.bpm == 120
        assert h.num_segments == 3
        assert h.rights["creator_name"] == "홍길동"

    def test_wrong_magic(self):
        data = b"XXXX" + bytes([0x03]) + struct.pack(">I", 2) + b"{}"
        with pytest.raises(TL3ParseError, match="magic"):
            parse_header_bytes(data)

    def test_unsupported_version(self):
        header_json = b"{}"
        data = b"TLNK" + bytes([0x09]) + struct.pack(">I", len(header_json)) + header_json
        with pytest.raises(TL3ParseError, match="버전"):
            parse_header_bytes(data)

    def test_too_short(self):
        with pytest.raises(TL3ParseError):
            parse_header_bytes(b"TLNK")

    def test_bad_json(self):
        data = b"TLNK" + bytes([0x03]) + struct.pack(">I", 5) + b"not-json"
        with pytest.raises(TL3ParseError, match="JSON"):
            parse_header_bytes(data)

    def test_truncated_json(self):
        data = b"TLNK" + bytes([0x03]) + struct.pack(">I", 100) + b"{}"
        with pytest.raises(TL3ParseError, match="headerLen"):
            parse_header_bytes(data)


class TestTL3Header:
    def test_assert_music_ok(self):
        data = make_tl3_bytes(SAMPLE_HEADER)
        h = parse_header_bytes(data)
        h.assert_music()

    def test_assert_music_fail(self):
        header = dict(SAMPLE_HEADER, kind="video")
        data = make_tl3_bytes(header)
        h = parse_header_bytes(data)
        with pytest.raises(TL3ParseError, match="음원이 아닙니다"):
            h.assert_music()


class TestParseHeaderFile:
    def test_missing_file(self, tmp_path: Path):
        with pytest.raises(TL3ParseError, match="존재하지 않"):
            parse_header(tmp_path / "nope.tl3")

    def test_valid_file(self, tmp_path: Path):
        p = tmp_path / "sample.tl3"
        p.write_bytes(make_tl3_bytes(SAMPLE_HEADER))
        h = parse_header(p)
        assert h.title == "테스트 곡"
        assert h.fid == "test-fid-001"
