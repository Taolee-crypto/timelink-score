"""MusicXML → PDF 렌더링 (MuseScore CLI).

원칙 3 준수: MuseScore는 외부 도구. 결과 PDF만 저장.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

_MUSESCORE_CANDIDATES = (
    "mscore",
    "musescore",
    "musescore4",
    "mscore4",
    "MuseScore4",
)


class RenderError(Exception):
    """PDF 렌더링 실패."""


def find_musescore() -> str | None:
    """PATH에서 MuseScore 실행 파일을 찾는다."""
    for name in _MUSESCORE_CANDIDATES:
        p = shutil.which(name)
        if p:
            return p
    return None


def render_pdf(
    musicxml_path: str | Path,
    out_pdf: str | Path,
    *,
    mscore_bin: str | None = None,
) -> Path:
    """MusicXML을 MuseScore CLI로 PDF 변환."""
    musicxml_path = Path(musicxml_path).resolve()
    if not musicxml_path.exists():
        raise RenderError(f"MusicXML 파일이 없습니다: {musicxml_path}")

    out_pdf = Path(out_pdf).resolve()
    out_pdf.parent.mkdir(parents=True, exist_ok=True)

    exe = mscore_bin or find_musescore()
    if not exe:
        raise RenderError(
            "MuseScore를 찾을 수 없습니다. https://musescore.org/download "
            "에서 설치 후 PATH에 추가하거나, mscore_bin 인자로 경로를 지정하세요."
        )

    cmd = [exe, "-o", str(out_pdf), str(musicxml_path)]

    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        raise RenderError(
            f"MuseScore 실행 실패 (exit={e.returncode}): "
            f"{e.stderr.decode(errors='ignore')[:500]}"
        ) from e

    if not out_pdf.exists():
        raise RenderError(
            f"PDF가 생성되지 않았습니다. MuseScore 출력을 확인하세요: {out_pdf}"
        )

    logger.info("PDF 생성: %s", out_pdf)
    return out_pdf
