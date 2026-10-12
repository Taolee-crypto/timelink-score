"""TL3 헤더에 악보 데이터 삽입/추출."""

from __future__ import annotations

import hashlib
import json
import logging
import struct
from pathlib import Path
from typing import Any

from .compressor import (
    ScoreCompressError,
    compress_if_beneficial,
    decompress_auto,
)
from .schema import ScoreData, SCORE_SCHEMA_VERSION

logger = logging.getLogger(__name__)


class PackerError(Exception):
    """TL3 헤더 pack/unpack 실패."""


TLNK_MAGIC = b"TLNK"
HEADER_PREFIX_LEN = 9


def _score_to_header_payload(score: ScoreData) -> dict[str, Any]:
    raw = score.to_dict()

    json_str = json.dumps(raw, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    score_hash = hashlib.sha256(json_str.encode("utf-8")).hexdigest()
    raw["score_hash"] = score_hash

    encoded, is_compressed = compress_if_beneficial(raw)

    return {
        "compressed": is_compressed,
        "data": encoded,
    }


def _header_payload_to_score(payload: dict[str, Any]) -> ScoreData:
    if not payload:
        raise PackerError("빈 score payload")

    is_compressed = bool(payload.get("compressed", False))
    encoded = payload.get("data")

    if encoded is None:
        raise PackerError("score payload에 data 없음")

    try:
        raw = decompress_auto(encoded, is_compressed)
    except ScoreCompressError as e:
        raise PackerError(f"score 해제 실패: {e}") from e

    saved_hash = raw.pop("score_hash", None)
    if saved_hash:
        json_str = json.dumps(raw, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        actual_hash = hashlib.sha256(json_str.encode("utf-8")).hexdigest()
        if actual_hash != saved_hash:
            logger.warning("score_hash 불일치")

    return ScoreData.from_dict(raw)


def _read_tl3_header(path: Path) -> tuple[int, dict[str, Any], int]:
    """TL3 파일에서 헤더 파싱."""
    with path.open("rb") as f:
        prefix = f.read(HEADER_PREFIX_LEN)
        if len(prefix) < HEADER_PREFIX_LEN:
            raise PackerError("파일이 너무 짧음")

        magic = prefix[0:4]
        if magic != TLNK_MAGIC:
            raise PackerError(f"TLNK magic 불일치: {magic!r}")

        version = prefix[4]
        (header_len,) = struct.unpack(">I", prefix[5:9])

        header_bytes = f.read(header_len)
        if len(header_bytes) != header_len:
            raise PackerError("헤더 잘림")

    try:
        header = json.loads(header_bytes.decode("utf-8"))
    except Exception as e:
        raise PackerError(f"헤더 JSON 파싱 실패: {e}") from e

    return version, header, HEADER_PREFIX_LEN + header_len


def _write_tl3_header(
    src: Path,
    dst: Path,
    version: int,
    header: dict[str, Any],
    *,
    preserve_segments: bool = True,
) -> None:
    """새 헤더로 TL3 파일 재작성 (세그먼트는 그대로 복사)."""
    header_json = json.dumps(header, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

    new_prefix = TLNK_MAGIC + bytes([version]) + struct.pack(">I", len(header_json))

    with src.open("rb") as fin, dst.open("wb") as fout:
        # 원본 prefix 읽기 (9 바이트)
        old_prefix = fin.read(HEADER_PREFIX_LEN)
        if len(old_prefix) < HEADER_PREFIX_LEN:
            raise PackerError("원본 prefix 부족")

        # 원본 헤더 길이 (prefix의 5~8 바이트)
        (old_header_len,) = struct.unpack(">I", old_prefix[5:9])

        # 세그먼트 시작 위치로 이동
        fin.seek(HEADER_PREFIX_LEN + old_header_len)

        # 새 prefix + 헤더 쓰기
        fout.write(new_prefix)
        fout.write(header_json)

        # 세그먼트 복사
        if preserve_segments:
            while True:
                chunk = fin.read(1024 * 1024)
                if not chunk:
                    break
                fout.write(chunk)


def embed_score_in_tl3(
    tl3_path: str | Path,
    score: ScoreData,
    *,
    out_path: str | Path | None = None,
    in_place: bool = False,
) -> Path:
    """TL3 파일 헤더에 악보 데이터를 삽입."""
    tl3_path = Path(tl3_path)
    if not tl3_path.exists():
        raise PackerError(f"TL3 파일 없음: {tl3_path}")

    version, header, _ = _read_tl3_header(tl3_path)
    header["score"] = _score_to_header_payload(score)

    if in_place:
        tmp = tl3_path.with_suffix(".tl3.tmp")
        _write_tl3_header(tl3_path, tmp, version, header)
        tmp.replace(tl3_path)
        out_path = tl3_path
    else:
        if out_path is None:
            out_path = tl3_path.with_name(tl3_path.stem + ".with_score.tl3")
        out_path = Path(out_path)
        _write_tl3_header(tl3_path, out_path, version, header)

    logger.info("악보 데이터 삽입 완료: %s", out_path)
    return out_path


def extract_score_from_tl3(tl3_path: str | Path) -> ScoreData | None:
    """TL3 파일 헤더에서 악보 데이터를 추출."""
    tl3_path = Path(tl3_path)
    if not tl3_path.exists():
        raise PackerError(f"TL3 파일 없음: {tl3_path}")

    _, header, _ = _read_tl3_header(tl3_path)

    payload = header.get("score")
    if not payload:
        return None

    return _header_payload_to_score(payload)