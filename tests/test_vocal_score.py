"""Vocal stem + time-aligned registered lyrics → *real MusicXML lyrics*.

Heavy Demucs/WhisperX models are mocked here; unit tests do not claim their
acoustic output accuracy. End-to-end sung Korean recordings require a GPU test.
"""
from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from music21 import converter
from timelink_score.melody.extract import NoteEvent, _frames_to_notes
from timelink_score.vocal_score import (
    TimedWord,VocalScoreError,lyrics_on_sung_notes,
    create_vocal_lyric_score,
)
class VocalScoreTest(unittest.TestCase):
    def setUp(self):
        self.notes=[
            NoteEvent(start=0,end=.32,midi=60,freq=261.63,confidence=.92),
            NoteEvent(start=.32,end=.64,midi=62,freq=293.66,confidence=.90),
            NoteEvent(start=.8,end=1.12,midi=64,freq=329.63,confidence=.91),
            NoteEvent(start=1.12,end=1.44,midi=65,freq=349.23,confidence=.88),
            NoteEvent(start=1.44,end=1.8,midi=67,freq=392.0,confidence=.93),
        ]
        self.words=[TimedWord("너를",0,.64),TimedWord("사랑해",.8,1.8)]
    def test_timed_korean_lyrics_attach_to_melody(self):
        result=lyrics_on_sung_notes(self.notes,self.words)
        self.assertEqual(len(result),5)
        self.assertEqual("".join(e["lyric"] for e in result),"너를사랑해")
        self.assertEqual([e["m"] for e in result],[60,62,64,65,67])
    def test_unmatched_words_rejected_not_fabricated(self):
        with self.assertRaises(VocalScoreError):
            lyrics_on_sung_notes(self.notes,[TimedWord("없는가사",40,45)])
    def test_silence_must_not_create_a_voice_note(self):
        notes=_frames_to_notes(times=[0,.2,.4,.6,.8,1.0,1.2,1.4,1.6,1.8],
                              midi=[-1,-1,60,60,-1,-1,62,62,-1,-1],
                              freq=[0,0,261,261,0,0,293,293,0,0],
                              conf=[0,0,.9,.9,0,0,.8,.8,0,0],
                              min_duration=.1)
        self.assertEqual([n.midi for n in notes],[60,62])
    def test_musicxml_contains_actual_korean_lyric_elements(self):
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/"source.wav"
            source.write_bytes(b"placeholder for mocked Demucs"+bytes(5000))
            def fake_separate(audio,out_dir,**_):
                p=Path(out_dir)/"vocals.wav"
                p.parent.mkdir(parents=True,exist_ok=True)
                p.write_bytes(bytes(6000))
                return p
            with patch("timelink_score.vocal_score.separate_vocals",side_effect=fake_separate),\
                 patch("timelink_score.vocal_score.extract_melody",return_value=self.notes),\
                 patch("timelink_score.vocal_score.verified_word_alignment",return_value=self.words):
                response=create_vocal_lyric_score(
                    source, "너를 사랑해", out_dir=Path(temp)/"out",
                    title="보컬 악보 테스트",bpm=100,device="cpu")
            xml=response["musicxml"].read_text(encoding="utf-8")
            self.assertIn("<lyric",xml)
            self.assertIn("너",xml)
            self.assertIn("사",xml)
            obj=converter.parse(str(response["musicxml"]))
            self.assertEqual("".join(n.lyric for n in obj.recurse().notes if n.lyric),"너를사랑해")
            data=json.loads(response["score_json"].read_text(encoding="utf-8"))
            self.assertTrue(data["analysis"]["vocals_separated"])
            self.assertTrue(data["analysis"]["lyrics_aligned"])
            self.assertFalse(data["tld_issued"])
            self.assertEqual(data["tl_charged"],0)
            self.assertEqual(data["quality"],"needs_singer_and_lyric_review")
if __name__=="__main__":
    unittest.main()
