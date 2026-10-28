"""Verified vocal-melody lead sheet with lyrics.

Only source-separated singer audio is eligible for pitched-note transcription.
Never feed the original full mix into YIN/CREPE. Lyric timestamps must come
from an actual forced-alignment model, not guessed uniformly over the track.
"""
from __future__ import annotations

import difflib
import json
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .audio.separate import separate_vocals
from .melody.extract import NoteEvent, extract_melody

class VocalScoreError(RuntimeError):
    pass

def _compact(text: str) -> str:
    return "".join(c for c in str(text).casefold() if c.isalnum())

def _lyric_words(text: str) -> list[str]:
    return re.findall(r"[^\W_]+(?:['’][^\W_]+)?", str(text), flags=re.UNICODE)

@dataclass(frozen=True)
class TimedWord:
    text: str
    start: float
    end: float

def verified_word_alignment(vocals: Path, registered_lyrics: str, *, language: str = "ko", device: str = "cpu") -> list[TimedWord]:
    """WhisperX vocals-only ASR & word alignment with fail-closed lyrics check.

    Singing often defeats speech alignment, so mismatched words/times are
    rejected rather than attaching fabricated syllables to arbitrary notes.
    """
    lyrics = _lyric_words(registered_lyrics)
    if not lyrics:
        raise VocalScoreError("TRACK에 등록된 가사가 없어 악보의 노랫말을 정렬할 수 없습니다.")
    try:
        import whisperx
    except ImportError as exc:
        raise VocalScoreError("WhisperX 가사 정렬 모델이 설치되지 않았습니다.") from exc
    try:
        audio = whisperx.load_audio(str(vocals))
        model = whisperx.load_model("medium", device, compute_type="float16" if device.startswith("cuda") else "int8")
        result = model.transcribe(audio, batch_size=8, language=language)
        del model
        if not result.get("segments"):
            raise VocalScoreError("분리된 보컬에서 가사를 인식하지 못했습니다.")
        alignment_model, metadata = whisperx.load_align_model(language_code=language, device=device)
        aligned = whisperx.align(result["segments"], alignment_model, metadata, audio, device, return_char_alignments=False)
        del alignment_model
    except VocalScoreError:
        raise
    except Exception as exc:
        raise VocalScoreError("보컬 음성과 가사 시간 정렬에 실패했습니다. 모델 설정과 노랫말을 확인해 주세요.") from exc
    aligned_words = []
    for segment in aligned.get("segments", []):
        for word in segment.get("words", []):
            if "start" in word and "end" in word and _compact(word.get("word", "")):
                aligned_words.append(TimedWord(str(word["word"]), float(word["start"]), float(word["end"])))
    if not aligned_words:
        raise VocalScoreError("음절에 연결할 보컬 발음 시간이 감지되지 않았습니다.")
    # Do not silently insert ASR-imagined words. Require the exact registered
    # words after punctuation/case cleanup; review/fix lyrics when mismatched.
    recognized = [_compact(w.text) for w in aligned_words]
    expected = [_compact(w) for w in lyrics]
    if recognized != expected:
        score = difflib.SequenceMatcher(a=" ".join(expected), b=" ".join(recognized), autojunk=False).ratio()
        raise VocalScoreError(f"등록 가사와 보컬 인식이 일치하지 않습니다 (일치도 {score:.0%}). 가사 또는 음성 정렬을 검수해야 합니다.")
    if any(w.start<0 or w.end<=w.start or (i>0 and w.start<aligned_words[i-1].start)
           for i,w in enumerate(aligned_words)):
        raise VocalScoreError("가사 정렬 시각이 올바르지 않습니다.")
    return [TimedWord(text=lyrics[i], start=w.start, end=w.end) for i,w in enumerate(aligned_words)]

def lyrics_on_sung_notes(notes: list[NoteEvent], words: list[TimedWord]) -> list[dict[str,Any]]:
    """Map real aligned syllables to the nearest overlapping sung-note onset.

    A syllable may be sung over several notes (melisma). We mark the first
    onset; remaining tied notes are intentionally not assigned fake syllables.
    """
    if not notes or not words:
        raise VocalScoreError("가사와 보컬 음표가 모두 필요합니다.")
    notes = sorted(notes, key=lambda n:n.start)
    assigned: dict[int,list[str]] = {}
    for word in words:
        chars = [c for c in word.text if c.isalnum()]
        if not chars:
            continue
        available = [i for i,n in enumerate(notes)
                     if n.end>word.start and n.start<word.end and n.confidence>=0.5]
        if not available:
            raise VocalScoreError(f"'{word.text}' 가사에 대응하는 보컬 음표를 찾지 못했습니다.")
        for j,ch in enumerate(chars):
            target=word.start+(j+.5)*(word.end-word.start)/len(chars)
            nearest=min(available,key=lambda i:abs(max(notes[i].start,word.start)-target))
            assigned.setdefault(nearest,[]).append(ch)
    mapped=[]
    for i,note in enumerate(notes):
        text="".join(assigned.get(i,[]))
        mapped.append({"s":round(note.start,3),"d":round(note.duration,3),
                       "m":note.midi,"conf":round(note.confidence,3),"lyric":text})
    if not any(n["lyric"] for n in mapped):
        raise VocalScoreError("가사가 붙은 음표를 생성하지 못했습니다.")
    return mapped

def create_vocal_lyric_score(
    original_audio: str | Path, registered_lyrics: str, *,
    out_dir: str | Path, title: str, artist: str = "", bpm: float = 120,
    language: str = "ko", device: str = "cpu", rights: dict | None = None,
) -> dict[str,Any]:
    """Demucs → pitch from vocals ONLY → WhisperX actual lyric times → MusicXML.

    Requires a dedicated secure analysis worker with Demucs, torchcrepe and
    WhisperX models installed; Cloudflare edge JS cannot execute these models.
    The input must come from a verified rights-holder V5 asset, never an
    arbitrary public listener's decrypted playback.
    """
    from .leadsheet.assemble import assemble_leadsheet
    if not (40<=float(bpm)<=220):
        raise VocalScoreError("정확한 BPM(40~220)을 지정해야 합니다.")
    if not _lyric_words(registered_lyrics):
        raise VocalScoreError("곡에 등록된 가사가 없습니다.")
    source=Path(original_audio).resolve()
    if not source.is_file() or source.stat().st_size==0:
        raise VocalScoreError("분석 권한이 있는 원본 음원 파일이 없습니다.")
    with tempfile.TemporaryDirectory(prefix="timelink_vocals_") as scratch:
        vocal_file=separate_vocals(source, Path(scratch)/"separated", device=device)
        if not vocal_file.exists() or vocal_file.stat().st_size<2048:
            raise VocalScoreError("보컬 분리 결과가 비어 있습니다. 악보를 생성하지 않습니다.")
        # No fallback to the MIX. If CREPE is unavailable, fail rather than
        # claiming drum/bass frequencies are a singer's melody.
        sung=extract_melody(vocal_file, confidence_threshold=.65, min_note_duration=.10, device=device)
        sung=[n for n in sung if n.confidence>=.65 and n.duration>=.10 and 40<=n.midi<=90]
        if len(sung)<3:
            raise VocalScoreError("보컬 음정이 충분하지 않아 채보하지 않았습니다.")
        words=verified_word_alignment(vocal_file,registered_lyrics,language=language,device=device)
        mapped=lyrics_on_sung_notes(sung,words)
        score=assemble_leadsheet(melody=sung,chords=[],bpm=bpm,title=title,artist=artist,rights=rights)
        from music21 import note as m21note
        music_notes=[n for n in score.parts[0].recurse().notes if isinstance(n,m21note.Note)]
        if len(music_notes)!=len(mapped):
            raise VocalScoreError("보컬 음표와 악보 출력 음표 수가 일치하지 않습니다.")
        for note, event in zip(music_notes,mapped):
            if event["lyric"]:
                note.lyric=event["lyric"]
        out=Path(out_dir).resolve()
        out.mkdir(parents=True,exist_ok=True)
        xml=out/"vocal-lyrics.musicxml"
        score.write("musicxml",fp=str(xml))
        result={"version":1,"algorithm":"timelink-score-vocal-lyrics-v1",
                "quality":"needs_singer_and_lyric_review",
                "title":title,"artist":artist,"bpm":bpm,"time_signature":"4/4",
                "melody":mapped,"lyrics":[{"s":w.start,"e":w.end,"text":w.text} for w in words],
                "analysis":{"vocals_separated":True,"source":"verified_vocal_stem",
                            "lyrics_aligned":True,"language":language},
                "tld_issued":False,"tl_charged":0}
        (out/"vocal-score-draft.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
        return {"score_json":out/"vocal-score-draft.json","musicxml":xml,"notes":len(mapped),
                "status":"review_required"}
