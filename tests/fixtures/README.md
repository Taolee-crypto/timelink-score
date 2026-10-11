# Test Fixtures

테스트용 TL3 샘플을 여기에 둡니다.

## sample_minimal.tl3

`.gitignore`가 `*.tl3`를 무시하지만, `sample_minimal.tl3`는 예외로 커밋됩니다.
(민감 정보 없이, 헤더 파서 테스트용으로만 사용)

샘플 생성 방법:

    import json, struct
    header = {"v": 3, "kind": "music", "title": "test", "bpm": 120, "fid": "x",
              "mp3": {"N": 1}}
    data = b"TLNK" + bytes([0x03]) + struct.pack(">I", len(json.dumps(header))) \
           + json.dumps(header).encode() + b"\x00" * 176400
    open("tests/fixtures/sample_minimal.tl3", "wb").write(data)
