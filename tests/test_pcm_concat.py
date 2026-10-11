"""PCM 이어붙이기 테스트."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from timelink_score.audio.pcm_concat import (  # noqa: E402
    PCMConcatError,
    concat_segments_to_array,
    concat_segments_to_wav,
)


def make_pcm16(samples: list[int], channels: int = 1) -> bytes:
    arr = np.array(samples, dtype="<i2")
    return arr.tobytes()


class TestConcatToArray:
    def test_mono_single_segment(self):
        seg = make_pcm16([0, 16384, -16384, 32767])
        arr = concat_segments_to_array([seg], sample_rate=44100, channels=1)
        assert arr.shape == (4, 1)
        assert arr.dtype == np.float32
        assert np.isclose(arr[1, 0], 0.5, atol=1e-4)

    def test_stereo(self):
        # 2 frames × 2ch = 4 samples
        seg = make_pcm16([100, -100, 200, -200])
        arr = concat_segments_to_array([seg], sample_rate=44100, channels=2)
        assert arr.shape == (2, 2)

    def test_multiple_segments(self):
        s1 = make_pcm16([0, 0])
        s2 = make_pcm16([0, 0])
        arr = concat_segments_to_array([s1, s2], sample_rate=44100, channels=1)
        assert arr.shape == (4, 1)

    def test_empty_raises(self):
        with pytest.raises(PCMConcatError, match="비어"):
            concat_segments_to_array([], sample_rate=44100, channels=1)

    def test_bad_channels(self):
        with pytest.raises(PCMConcatError, match="채널"):
            concat_segments_to_array([b"\x00\x00"], sample_rate=44100, channels=3)

    def test_odd_length(self):
        # 3 bytes → PCM16 아님
        with pytest.raises(PCMConcatError):
            concat_segments_to_array([b"\x00\x00\x00"], sample_rate=44100, channels=1)


class TestConcatToWav:
    def test_write_wav(self, tmp_path: Path):
        seg1 = make_pcm16([1000, 2000, 3000])
        seg2 = make_pcm16([-1000, -2000, -3000])
        out = tmp_path / "out.wav"
        p = concat_segments_to_wav(
            [seg1, seg2], out, sample_rate=44100, channels=1
        )
        assert p.exists()
        assert p.stat().st_size > 44  # WAV 헤더 + 데이터
