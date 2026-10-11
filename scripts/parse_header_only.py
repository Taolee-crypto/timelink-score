"""헤더만 파싱 (TL 소모 없음) — 빠른 확인용.

사용:
    python scripts/parse_header_only.py song.tl3
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from timelink_score.tl3.header_parser import parse_header  # noqa: E402


def main() -> int:
    if len(sys.argv) < 2:
        print("사용: python scripts/parse_header_only.py <song.tl3>")
        return 1

    path = Path(sys.argv[1])
    try:
        h = parse_header(path)
    except Exception as e:
        print(f"❌ {e}")
        return 1

    print(json.dumps(h.raw, ensure_ascii=False, indent=2))
    print()
    print(f"🎼 kind={h.kind}, title={h.title}, bpm={h.bpm}, N={h.num_segments}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
