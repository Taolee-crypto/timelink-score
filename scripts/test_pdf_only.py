"""PDF 렌더링 단독 테스트."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from timelink_score.score import find_lilypond, render_pdf

xml = Path("output") / "test_leadsheet.musicxml"
pdf = Path("output") / "test_leadsheet.pdf"

print("LilyPond:", find_lilypond())
print("Input exists:", xml.exists())
print("렌더링 시작...")

try:
    result = render_pdf(xml, pdf)
    print("SUCCESS:", result)
except Exception as e:
    print("FAIL:", type(e).__name__, e)
    sys.exit(1)
