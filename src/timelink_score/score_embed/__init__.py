"""악보 데이터 TL3 헤더 임베드.

- schema: ScoreData, NoteData, ChordData, KeyData, LyricData
- compressor: gzip + base64
- packer: TL3 헤더 삽입/추출
"""

from .compressor import (
    ScoreCompressError,
    compress_if_beneficial,
    compress_score,
    decompress_auto,
    decompress_score,
)
from .packer import (
    PackerError,
    embed_score_in_tl3,
    extract_score_from_tl3,
)
from .schema import (
    SCORE_SCHEMA_VERSION,
    ChordData,
    KeyData,
    LyricData,
    NoteData,
    ScoreData,
)

__all__ = [
    # schema
    "ScoreData",
    "NoteData",
    "ChordData",
    "KeyData",
    "LyricData",
    "SCORE_SCHEMA_VERSION",
    # compressor
    "compress_score",
    "decompress_score",
    "compress_if_beneficial",
    "decompress_auto",
    "ScoreCompressError",
    # packer
    "embed_score_in_tl3",
    "extract_score_from_tl3",
    "PackerError",
]