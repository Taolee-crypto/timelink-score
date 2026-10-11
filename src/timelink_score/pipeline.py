"""전체 파이프라인 오케스트레이션.

TL3 → 악보(PDF)까지의 전체 흐름:
    1. 헤더 파싱
    2. 세그먼트 순차 fetch (스파인)
    3. PCM 이어붙이기 → 임시 WAV
    4. Demucs 보컬 분리
    5. Basic Pitch → MIDI
    6. 조성 분석
    7. music21 → MusicXML (저작권자 정보 포함)
    8. MuseScore → PDF
    9. meta.json 저장
"""

from __future__ import annotations

import json
import logging
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .audio.pcm_concat import concat_segments_to_wav
from .audio.separate import separate_vocals
from .key.analyze import KeyResult, analyze_key
from .pitch.extract import extract_midi
from .score.builder import build_score
from .score.render import render_pdf
from .tl3.header_parser import TL3Header, parse_header
from .tl3.segment_client import SegmentClient

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """파이프라인 실행 결과."""

    musicxml: Path | None = None
    pdf: Path | None = None
    midi: Path | None = None
    meta_json: Path | None = None
    key_result: KeyResult | None = None
    header: TL3Header | None = None
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "musicxml": str(self.musicxml) if self.musicxml else None,
            "pdf": str(self.pdf) if self.pdf else None,
            "midi": str(self.midi) if self.midi else None,
            "meta_json": str(self.meta_json) if self.meta_json else None,
            "key": {
                "name": self.key_result.name if self.key_result else None,
                "korean": self.key_result.korean if self.key_result else None,
                "confidence": self.key_result.confidence if self.key_result else None,
                "sharps_flats": self.key_result.sharps_flats if self.key_result else None,
            } if self.key_result else None,
            "title": self.header.title if self.header else None,
            "artist": self.header.artist if self.header else None,
            "warnings": self.warnings,
        }


def run_pipeline(
    tl3_path: str | Path,
    *,
    out_dir: str | Path = "output",
    server_base: str,
    session_id: str,
    auth_token: str | None = None,
    time_signature: str = "4/4",
    quantize_grid: str = "16th",
    skip_vocal_separation: bool = False,
    skip_pdf: bool = False,
    work_dir: str | Path | None = None,
) -> PipelineResult:
    """TL3 → PDF 전체 파이프라인 실행."""
    tl3_path = Path(tl3_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    result = PipelineResult()

    # 1. 헤더 파싱
    logger.info("1) 헤더 파싱: %s", tl3_path)
    header = parse_header(tl3_path)
    header.assert_music()
    result.header = header
    logger.info(
        "   제목=%s, 아티스트=%s, BPM=%s, 세그먼트=%s",
        header.title, header.artist, header.bpm, header.num_segments,
    )

    if header.num_segments <= 0:
        raise ValueError("헤더에 세그먼트 수(N)가 없습니다.")

    # 임시 작업 폴더
    tmp_ctx = (
        tempfile.TemporaryDirectory(prefix="tlscore_")
        if work_dir is None
        else None
    )
    if tmp_ctx is not None:
        work = Path(tmp_ctx.name)
    else:
        work = Path(work_dir)
        work.mkdir(parents=True, exist_ok=True)

    try:
        # 2~3. 세그먼트 fetch → WAV
        logger.info("2~3) 세그먼트 순차 fetch → WAV")
        mix_wav = work / "mix.wav"

        with SegmentClient(
            base_url=server_base,
            fid=header.fid,
            session_id=session_id,
            auth_token=auth_token,
        ) as client:
            segments = client.iter_segments(header.num_segments)
            concat_segments_to_wav(
                segments,
                mix_wav,
                sample_rate=header.sample_rate or 44100,
                channels=header.channels or 2,
            )
            logger.info("   남은 TL: %s", client.balance)

        # 4. 보컬 분리
        if skip_vocal_separation:
            logger.info("4) 보컬 분리 생략")
            vocals_wav = mix_wav
        else:
            logger.info("4) Demucs 보컬 분리")
            vocals_wav = separate_vocals(mix_wav, work / "demucs")

        # 5. 피치 추출
        logger.info("5) 피치 추출 → MIDI")
        midi_path = extract_midi(vocals_wav, work / "midi")
        result.midi = midi_path

        # 6. 조성 분석
        logger.info("6) 조성 분석")
        key_result = analyze_key(vocals_wav)
        result.key_result = key_result
        logger.info(
            "   조성=%s (%s), 신뢰도=%.3f",
            key_result.name, key_result.korean, key_result.confidence,
        )

        # 7. MusicXML
        logger.info("7) MusicXML 생성")
        musicxml_path = out_dir / "score.musicxml"
        build_score(
            midi_path,
            musicxml_path,
            key_result=key_result,
            bpm=header.bpm or None,
            time_signature=time_signature,
            title=header.title,
            artist=header.artist,
            rights=header.rights,
            quantize=True,
            quantize_grid=quantize_grid,
        )
        result.musicxml = musicxml_path

        # 8. PDF
        if skip_pdf:
            logger.info("8) PDF 렌더링 생략")
        else:
            logger.info("8) PDF 렌더링")
            pdf_path = out_dir / "score.pdf"
            render_pdf(musicxml_path, pdf_path)
            result.pdf = pdf_path

        # 9. meta.json
        logger.info("9) meta.json 저장")
        meta_path = out_dir / "meta.json"
        meta_payload = {
            "header": header.raw,
            "pipeline": result.to_dict(),
        }
        meta_path.write_text(
            json.dumps(meta_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        result.meta_json = meta_path

    finally:
        if tmp_ctx is not None:
            tmp_ctx.cleanup()

    logger.info("✅ 파이프라인 완료")
    return result
