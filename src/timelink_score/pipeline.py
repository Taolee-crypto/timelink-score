"""Real audio -> editable MusicXML / TRACK ScoreData draft.

This is intentionally a *local, rights-holder supplied audio* path. It never
decrypts V5 TL3, touches a listener's TL or pretends to issue a paid TLD file.
Secure V5 server-side capture, transcription-worker jobs and TLD settlement are
independent future integrations.
"""
from __future__ import annotations

import json
import logging
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)
_AUDIO_EXTS = {".wav", ".mp3", ".flac", ".m4a", ".ogg"}
_MAX_SECONDS = 180
_MAX_SIZE = 50 * 1024 * 1024


@dataclass
class PipelineResult:
    musicxml: Path | None
    pdf: Path | None
    meta_json: Path | None
    key_result: object | None
    score_data_path: Path | None = None


def _fallback_melody(path: Path):
    """librosa YIN fallback on pitched mono audio when torchcrepe is absent."""
    import librosa
    import numpy as np
    from .melody.extract import NoteEvent

    y, sr = librosa.load(str(path), sr=16000, mono=True, duration=_MAX_SECONDS)
    if y.size < sr // 3:
        raise ValueError("오디오가 너무 짧습니다.")
    frame_length = 2048
    hop = 256
    f0 = librosa.yin(y, fmin=85, fmax=900, sr=sr,
                     frame_length=frame_length, hop_length=hop)
    rms = librosa.feature.rms(y=y, frame_length=frame_length,
                             hop_length=hop, center=True)[0]
    length = min(len(f0), len(rms))
    threshold = max(0.012, float(np.max(rms)) * .08)
    pitches = []
    for i in range(length):
        if rms[i] < threshold or not np.isfinite(f0[i]):
            pitches.append(None)
        else:
            m = int(round(float(librosa.hz_to_midi(f0[i]))))
            pitches.append(m if 40 <= m <= 90 else None)
    # Suppress one-frame jitter while preserving silent gaps.
    smoothed = []
    for i, midi in enumerate(pitches):
        if midi is None:
            smoothed.append(None)
            continue
        around = sorted(v for v in pitches[max(0,i-1):i+2] if v is not None)
        smoothed.append(around[len(around)//2] if around else midi)
    events = []
    start = 0
    for i in range(1, length+1):
        if i < length and smoothed[i] == smoothed[start]:
            continue
        midi = smoothed[start]
        dur = (i-start)*hop/sr
        if midi is not None and dur >= 0.12:
            events.append(NoteEvent(start=start*hop/sr, end=i*hop/sr,
                                    midi=midi, freq=float(librosa.midi_to_hz(midi)),
                                    confidence=.6))
        start = i
    return events


def run_local_audio(
    audio_path: str | Path,
    *,
    out_dir: str | Path = "output",
    title: str = "",
    artist: str = "",
    bpm: float = 120,
    time_signature: str = "4/4",
    rights: dict | None = None,
    separate_vocals: bool = False,
    include_chords: bool = True,
    render_pdf: bool = False,
) -> PipelineResult:
    """Analyze actual audio and write MusicXML plus a TRACK-compatible score JSON.

    Complex multitrack music may need manual note/chord review.
    No original audio is retained, transmitted or repackaged.
    """
    from .key.analyze import analyze_key
    from .chord.extract import extract_chords
    from .leadsheet.assemble import assemble_leadsheet
    from .score_embed.schema import ScoreData, KeyData, NoteData, ChordData

    src = Path(audio_path).expanduser().resolve()
    if not src.is_file() or src.suffix.lower() not in _AUDIO_EXTS:
        raise ValueError("로컬 WAV·MP3·FLAC·M4A·OGG 음원을 선택해 주세요.")
    if not 0 < src.stat().st_size <= _MAX_SIZE:
        raise ValueError("음원은 50MB 이하여야 합니다.")
    if not 40 <= bpm <= 220:
        raise ValueError("BPM은 40~220 사이여야 합니다.")
    out = Path(out_dir).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="tlscore_") as temp:
        analysis_path = src
        if separate_vocals:
            from .audio.separate import separate_vocals as demucs
            analysis_path = demucs(src, Path(temp) / "separated")

        try:
            # Prefer installed torchcrepe model; fall back to librosa YIN.
            from .melody.extract import extract_melody
            melody = extract_melody(analysis_path)
            method = "torchcrepe"
        except Exception as exc:
            logger.warning("torchcrepe unavailable or failed (%s); trying librosa YIN",exc)
            melody = _fallback_melody(analysis_path)
            method = "librosa-yin-fallback"
        if not melody:
            raise ValueError("추출한 음표가 없습니다. 반주가 섞인 경우 보컬 분리를 시도해 주세요.")

        key_result = analyze_key(src)
        chords = extract_chords(src) if include_chords else []
        score = assemble_leadsheet(melody=melody, chords=chords,
                                   key_result=key_result, bpm=bpm,
                                   time_signature=time_signature,
                                   title=title or src.stem, artist=artist, rights=rights)
        musicxml = out / "score.musicxml"
        score.write("musicxml", fp=str(musicxml))
        xml_file: Path = musicxml
        if not musicxml.is_file() or musicxml.stat().st_size < 100:
            raise RuntimeError("MusicXML 생성 실패")

        score_data = ScoreData(
            generated_at=datetime.now(timezone.utc).isoformat(),
            algorithm="timelink-score-local-"+method+"-v1",
            key=KeyData(tonic=key_result.tonic, mode=key_result.mode,
                        sharps_flats=key_result.sharps_flats, conf=key_result.confidence),
            time_signature=time_signature, bpm=bpm,
            melody=[NoteData(s=e.start, d=e.duration, m=e.midi, conf=e.confidence)
                    for e in melody],
            chords=[ChordData(s=e.start,e=e.end,sym=e.symbol) for e in chords],
        )
        data_file = out / "track-score-draft.json"
        data_file.write_text(json.dumps(score_data.to_dict(),ensure_ascii=False,indent=2),
                             encoding="utf-8")
        meta = out / "meta.json"
        meta.write_text(json.dumps({
            "title": title or src.stem, "artist": artist, "rights": rights or {},
            "status": "draft_manual_review_required", "source": "locally_authorized_audio",
            "melody_notes": len(melody), "chords": len(chords), "key": key_result.name,
            "original_audio_stored": False, "tld_issued": False, "tl_charged": 0,
            "musicxml": musicxml.name, "score_data": data_file.name
        },ensure_ascii=False,indent=2),encoding="utf-8")
        pdf = None
        if render_pdf:
            from .score.render import render_pdf_from_score
            pdf = render_pdf_from_score(score, out / "score.pdf")
        return PipelineResult(xml_file, pdf, meta, key_result, data_file)


def run_pipeline(tl3_path, **kwargs):
    """Refuse deprecated V3 segment fetching until the actual V5 rights
    entitlement / analysis session contract is implemented and verified."""
    raise NotImplementedError(
        "구형 V3 TL3 세그먼트 분석은 V5에서 지원하지 않습니다. "
        "창작자가 권한을 가진 오디오는 'tlscore local'로 분석하세요. "
        "V5 재생 파일 자동 분석은 별도의 인증·과금·분석 서버 연동이 필요합니다."
    )
