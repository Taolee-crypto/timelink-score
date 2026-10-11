"""Demucs를 이용한 보컬/반주 분리.

원칙 3 준수: Demucs는 외부 도구. 결과 WAV는 임시.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path


class SeparationError(Exception):
    """보컬 분리 실패."""


def separate_vocals(
    audio_path: str | Path,
    out_dir: str | Path,
    *,
    model: str = "htdemucs",
    two_stems: bool = True,
    device: str | None = None,
) -> Path:
    """Demucs CLI로 보컬을 분리하고 vocals.wav 경로를 반환."""
    audio_path = Path(audio_path).resolve()
    if not audio_path.exists():
        raise SeparationError(f"입력 오디오가 없습니다: {audio_path}")

    if shutil.which("demucs") is None:
        raise SeparationError(
            "demucs CLI를 찾을 수 없습니다. `pip install demucs` 후 다시 시도하세요."
        )

    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    cmd = ["demucs", "-n", model, "-o", str(out_dir)]
    if two_stems:
        cmd += ["--two-stems", "vocals"]
    if device:
        cmd += ["-d", device]
    cmd.append(str(audio_path))

    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        raise SeparationError(
            f"demucs 실행 실패 (exit={e.returncode}): "
            f"{e.stderr.decode(errors='ignore')[:500]}"
        ) from e

    vocals_path = out_dir / model / audio_path.stem / "vocals.wav"
    if not vocals_path.exists():
        raise SeparationError(f"분리 결과를 찾을 수 없습니다: {vocals_path}")

    return vocals_path


def separate_vocals_in_memory(
    pcm_array,
    sample_rate: int,
    *,
    model: str = "htdemucs",
    device: str | None = None,
):
    """(실험적) numpy 배열을 임시 WAV로 저장 → Demucs → 결과 배열 반환."""
    import numpy as np
    import soundfile as sf

    with tempfile.TemporaryDirectory(prefix="tlscore_") as tmp:
        tmp = Path(tmp)
        in_wav = tmp / "input.wav"
        sf.write(str(in_wav), pcm_array, samplerate=sample_rate, subtype="PCM_16")

        vocals_path = separate_vocals(
            in_wav, tmp / "out", model=model, two_stems=True, device=device
        )

        data, sr = sf.read(str(vocals_path), dtype="float32", always_2d=True)
        return np.asarray(data), sr
