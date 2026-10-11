"""TL3 (TLNK 컨테이너) 연동 모듈.

- header_parser: 평문 헤더 JSON 파싱
- segment_client: 서버 API로 세그먼트 PCM fetch (스파인 준수)
"""

from .header_parser import TL3Header, parse_header, TL3ParseError
from .segment_client import SegmentClient, SpineViolationError, TLBalanceError

__all__ = [
    "TL3Header",
    "parse_header",
    "TL3ParseError",
    "SegmentClient",
    "SpineViolationError",
    "TLBalanceError",
]
