"""MusicXML -> PDF rendering (via music21 -> .ly -> LilyPond -> PDF)."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


class RenderError(Exception):
    """PDF render failed."""


_LILYPOND_CANDIDATES = ("lilypond", "lilypond.exe")
_LILYPOND_COMMON_PATHS = [
    Path.home() / "LilyPond" / "bin",
    Path("C:/LilyPond/bin"),
    Path("C:/Program Files/LilyPond/bin"),
]


def find_lilypond() -> str | None:
    for name in _LILYPOND_CANDIDATES:
        p = shutil.which(name)
        if p:
            return p
    for base in _LILYPOND_COMMON_PATHS:
        for name in _LILYPOND_CANDIDATES:
            c = base / name
            if c.exists():
                return str(c)
    return None


def _configure_music21(lily_exe: str) -> None:
    """music21 환경에 LilyPond 경로 설정."""
    try:
        from music21 import environment
        env = environment.Environment()
        env["lilypondPath"] = lily_exe
        # music21이 캐시를 새로 고치도록
        env["lilypondVersion"] = None
        env["musicxmlPath"] = lily_exe
    except Exception as e:
        logger.warning("music21 환경 설정 실패: %s", e)


def render_pdf_from_score(
    score,
    out_pdf: str | Path,
    *,
    lilypond_bin: str | None = None,
    timeout: int = 300,
) -> Path:
    """music21 Score -> .ly -> PDF."""
    out_pdf = Path(out_pdf).resolve()
    out_dir = out_pdf.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    lily = lilypond_bin or find_lilypond()
    if not lily:
        raise RenderError("LilyPond not found.")

    # ★ music21에 LilyPond 경로 설정 ★
    _configure_music21(lily)

    ly_path = out_dir / (out_pdf.stem + ".ly")
    if ly_path.exists():
        ly_path.unlink()

    try:
        score.write("lilypond", fp=str(ly_path))
    except Exception as e:
        raise RenderError(f"music21 lilypond write failed: {e}") from e

    if not ly_path.exists():
        raise RenderError(f".ly not created: {ly_path}")

    expected_pdf = out_dir / (ly_path.stem + ".pdf")
    if expected_pdf.exists():
        expected_pdf.unlink()

    env = os.environ.copy()
    lily_dir = str(Path(lily).parent)
    if lily_dir not in env.get("PATH", ""):
        env["PATH"] = lily_dir + os.pathsep + env.get("PATH", "")

    cmd = [lily, "--pdf", "-o", str(out_dir), str(ly_path)]
    logger.info("LilyPond: %s", " ".join(cmd))

    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=timeout, env=env)
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode(errors="ignore")[:1500]
        raise RenderError(f"LilyPond failed (exit={e.returncode}):\n{stderr}") from e
    except subprocess.TimeoutExpired:
        raise RenderError(f"LilyPond timeout ({timeout}s)")

    if not expected_pdf.exists():
        raise RenderError(f"PDF not created: {expected_pdf}")

    if expected_pdf != out_pdf:
        shutil.move(str(expected_pdf), str(out_pdf))

    logger.info("PDF created: %s", out_pdf)
    return out_pdf


def render_pdf(
    musicxml_path: str | Path,
    out_pdf: str | Path,
    *,
    lilypond_bin: str | None = None,
    timeout: int = 300,
) -> Path:
    """MusicXML -> music21 -> .ly -> PDF."""
    from music21 import converter

    musicxml_path = Path(musicxml_path).resolve()
    if not musicxml_path.exists():
        raise RenderError(f"MusicXML not found: {musicxml_path}")

    try:
        score = converter.parse(str(musicxml_path))
    except Exception as e:
        raise RenderError(f"MusicXML parse failed: {e}") from e

    return render_pdf_from_score(
        score, out_pdf, lilypond_bin=lilypond_bin, timeout=timeout
    )
