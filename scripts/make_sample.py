import json, struct
from pathlib import Path

header = {
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

header_json = json.dumps(header, ensure_ascii=False).encode("utf-8")
data = b"TLNK" + bytes([0x03]) + struct.pack(">I", len(header_json)) + header_json
data += b"\x00" * (176400 * 3)

out = Path("tests/fixtures/sample_minimal.tl3")
out.write_bytes(data)
print(f"OK: {out} ({out.stat().st_size} bytes)")
