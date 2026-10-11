"""전체 파이프라인 실행 (TL 소모 발생).

사용:
    python scripts/run_all.py run song.tl3 --out output ^
        --server https://api.timelink.example --session <SID>
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from timelink_score.cli import app  # noqa: E402

if __name__ == "__main__":
    app()
