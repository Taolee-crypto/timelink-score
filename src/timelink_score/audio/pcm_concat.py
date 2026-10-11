"""세그먼트 PCM16 → WAV / numpy 배열 이어붙이기.

원칙 1 준수: 디스크 캐시 금지. 결과는 메모리(numpy) 또는 명시적 산출물 WAV.
원칙 2 준수: 입력 세그먼트는 순차(1..N)임을 전제.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Iterator

import numpy as np
import soundfile as sf


class PCMConcatError(Exception):
    """PCM 이어붙이기 실패."""


def concat_segments_to_array(
    segments: Iterable[bytes],
    *,
    sample_rate: int,
    channels: int,
    sample_width: int = 2,
) -> np.ndarray:
    """세그먼트 bytes들을 순차로 이어붙여 float32 numpy 배열 반환."""
    if channels not in (1, 2):
        raise PCMConcatError(f"지원하지 않는 채널 수: {channels}")
    if sample_width != 2:
        raise PCMConcatError(f"PCM16만 지원합니다 (sample_width={sample_width})")

    chunks: list[np.ndarray] = []
    for i, seg in enumerate(segments, start=1):
        if not isinstance(seg, (bytes, bytearray)):
            raise PCMConcatError(f"세그먼트 {i}: bytes가 아닙니다 ({type(seg)})")
        if len(seg) % (sample_width * channels) != 0:
            raise PCMConcatError(
                f"세그먼트 {i}: 길이({len(seg)})가 "
                f"sample_width*channels({sample_width*channels})의 배수가 아님"
            )
        arr = np.frombuffer(seg, dtype="<i2").astype(np.float32) / 32768.0
        if channels > 1:
            arr = arr.reshape(-1, channels)
        else:
            arr = arr.reshape(-1, 1)
        chunks.append(arr)

    if not chunks:
        raise PCMConcatError("세그먼트가 비어 있습니다.")

    return np.concatenate(chunks, axis=0)


def concat_segments_to_wav(
    segments: Iterable[bytes],
    out_path: str | Path,
    *,
    sample_rate: int,
    channels: int,
) -> Path:
    """세그먼트 bytes들을 이어붙여 WAV 파일로 저장."""
    arr = concat_segments_to_array(
        segments, sample_rate=sample_rate, channels=channels
    )

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    sf.write(
        str(out_path),
        arr,
        samplerate=sample_rate,
        subtype="PCM_16",
    )
    return out_path


def iter_segments_from_bytes(data: bytes, seg_bytes: int) -> Iterator[bytes]:
    """(테스트용) 하나의 bytes에서 seg_bytes 단위로 잘라 yield."""
    if seg_bytes <= 0:
        raise PCMConcatError(f"seg_bytes는 양수여야 합니다: {seg_bytes}")
    for off in range(0, len(data), seg_bytes):
        yield data[off : off + seg_bytes]
