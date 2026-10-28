"""End-to-end audio -> TRACK score JSON + MusicXML, no legacy TL3 dependency."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import soundfile as sf

from timelink_score.pipeline import run_local_audio, _fallback_melody


class ScorePipelineTest(unittest.TestCase):
    def test_synthesized_melody_to_musicxml(self):
        sr = 16000
        note_midi = [60,62,64,67]
        parts = []
        for m in note_midi:
            freq = 440 * 2 ** ((m - 69) / 12)
            t = np.arange(int(sr * .7), dtype=float) / sr
            envelope = np.minimum(1, np.minimum(t/.03, (.7-t)/.03)).clip(0,1)
            parts.append(.28 * np.sin(2*np.pi*freq*t) * envelope)
            parts.append(np.zeros(int(.14*sr)))
        y=np.concatenate(parts).astype("float32")
        with tempfile.TemporaryDirectory() as d:
            src=Path(d)/"original.wav"
            sf.write(src,y,sr)
            notes=_fallback_melody(src)
            pitches=[n.midi for n in notes]
            for midi in note_midi:
                self.assertIn(midi,pitches)
            result=run_local_audio(src,out_dir=Path(d)/"results",
                                    bpm=100,include_chords=False,render_pdf=False,
                                    title="Synthetic Test",rights={"creator_name":"test"})
            self.assertTrue(result.musicxml.is_file())
            self.assertIn("<score-partwise",result.musicxml.read_text())
            data=json.loads(result.score_data_path.read_text())
            self.assertEqual(data["bpm"],100)
            self.assertGreaterEqual(len(data["melody"]),4)
            meta=json.loads(result.meta_json.read_text())
            self.assertFalse(meta["original_audio_stored"])
            self.assertFalse(meta["tld_issued"])
            self.assertEqual(meta["tl_charged"],0)

    def test_invalid_file_rejected_without_metadata(self):
        with self.assertRaises(ValueError):
            run_local_audio("nonexistent.wav")
        with self.assertRaises(NotImplementedError):
            from timelink_score.pipeline import run_pipeline
            run_pipeline("legacy-v3.tl3")


if __name__=="__main__":
    unittest.main()
