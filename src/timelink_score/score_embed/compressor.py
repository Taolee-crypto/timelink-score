"""악보 데이터 압축/해제.

gzip + base64 인코딩.
"""

from __future__ import annotations

import base64
import gzip
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class ScoreCompressError(Exception):
    """압축/해제 실패."""


COMPRESS_THRESHOLD = 1024


def compress_score(data: dict[str, Any]) -> str:
    """악보 데이터 dict → gzip + base64 문자열."""
    try:
        json_bytes = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    except Exception as e:
        raise ScoreCompressError(f"JSON 직렬화 실패: {e}") from e

    try:
        gz_bytes = gzip.compress(json_bytes, compresslevel=9)
    except Exception as e:
        raise ScoreCompressError(f"gzip 압축 실패: {e}") from e

    return base64.b64encode(gz_bytes).decode("ascii")


def decompress_score(encoded: str) -> dict[str, Any]:
    """gzip + base64 문자열 → 악보 데이터 dict."""
    if not encoded:
        raise ScoreCompressError("빈 문자열")

    try:
        gz_bytes = base64.b64decode(encoded)
    except Exception as e:
        raise ScoreCompressError(f"base64 디코딩 실패: {e}") from e

    try:
        json_bytes = gzip.decompress(gz_bytes)
    except Exception as e:
        raise ScoreCompressError(f"gzip 해제 실패: {e}") from e

    try:
        return json.loads(json_bytes.decode("utf-8"))
    except Exception as e:
        raise ScoreCompressError(f"JSON 파싱 실패: {e}") from e


def compress_if_beneficial(data: dict[str, Any]) -> tuple[str, bool]:
    """압축이 이득이면 압축, 아니면 평문 JSON."""
    try:
        json_str = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    except Exception as e:
        raise ScoreCompressError(f"JSON 직렬화 실패: {e}") from e

    if len(json_str) < COMPRESS_THRESHOLD:
        return json_str, False

    compressed = compress_score(data)
    if len(compressed) >= len(json_str):
        return json_str, False

    return compressed, True


def decompress_auto(encoded: str, is_compressed: bool) -> dict[str, Any]:
    """압축 여부에 따라 자동 해제."""
    if is_compressed:
        return decompress_score(encoded)
    try:
        return json.loads(encoded)
    except Exception as e:
        raise ScoreCompressError(f"JSON 파싱 실패: {e}") from e