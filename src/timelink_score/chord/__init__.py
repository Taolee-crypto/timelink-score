"""코드 추출 모듈 — librosa 크로마 + 템플릿 매칭.

기타리스트/가수용 리드시트에 필요한 코드 진행을 추출.
컴파일 불필요 (순수 numpy/scipy/librosa).
"""

from .extract import (
    ChordEvent,
    ChordExtractionError,
    extract_chords,
    format_progression,
)
from .templates import PITCH_CLASSES, SYMBOLS, TEMPLATES

__all__ = [
    "ChordEvent",
    "ChordExtractionError",
    "extract_chords",
    "format_progression",
    "PITCH_CLASSES",
    "SYMBOLS",
    "TEMPLATES",
]
