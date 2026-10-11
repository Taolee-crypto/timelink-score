"""기본 사용 예제.

1) 헤더만 파싱 (TL 소모 없음)
2) 전체 파이프라인 (TL 소모 발생)
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from timelink_score.tl3.header_parser import parse_header


def example_header_only(tl3_path: str) -> None:
    """헤더만 파싱."""
    print(f"=== 헤더 파싱: {tl3_path} ===")
    h = parse_header(tl3_path)
    print(f"제목: {h.title}")
    print(f"아티스트: {h.artist}")
    print(f"BPM: {h.bpm}")
    print(f"길이: {h.dur_sec}초 ({h.num_segments} 세그먼트)")
    print(f"ISRC: {h.rights.get('isrc', '-')}")
    print(f"창작자: {h.rights.get('creator_name', '-')}")


def example_full_pipeline(tl3_path: str, server: str, session: str) -> None:
    """전체 파이프라인 (TL 소모).

    실행 시 TL이 차감됩니다.
    """
    from timelink_score.pipeline import run_pipeline

    result = run_pipeline(
        tl3_path,
        out_dir="output",
        server_base=server,
        session_id=session,
        skip_pdf=False,
    )
    print(f"MusicXML: {result.musicxml}")
    print(f"PDF: {result.pdf}")
    if result.key_result:
        print(f"조성: {result.key_result.korean} ({result.key_result.signature_str})")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용:")
        print("  헤더만:  python examples/basic_usage.py <song.tl3>")
        print("  전체:    (스크립트 내 example_full_pipeline 직접 호출)")
        sys.exit(1)

    example_header_only(sys.argv[1])

    # 전체 파이프라인은 주석 해제 후 사용
    # example_full_pipeline(
    #     sys.argv[1],
    #     server="https://api.timelink.example",
    #     session="<SESSION_ID>",
    # )
