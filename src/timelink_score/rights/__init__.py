"""저작권자 정보 (원칙 6: Creator Attribution).

TL 헤더의 rights 객체를 악보 상단에 자동 삽입.
"""

from .attribution import (
    build_metadata,
    format_attribution_lines,
    CreatorAttribution,
)

__all__ = [
    "build_metadata",
    "format_attribution_lines",
    "CreatorAttribution",
]
