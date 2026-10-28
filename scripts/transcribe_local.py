"""Transcribe real, locally authorized audio into TRACK MusicXML/ScoreData."""
from __future__ import annotations
import argparse
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"src"))
from timelink_score.pipeline import run_local_audio
p=argparse.ArgumentParser(description="TimeLink TRACK: local audio to editable score")
p.add_argument("audio",help="WAV/MP3/FLAC/M4A/OGG file you may analyze")
p.add_argument("--out",default="output")
p.add_argument("--bpm",type=float,default=120)
p.add_argument("--title",default="")
p.add_argument("--artist",default="")
p.add_argument("--no-chords",action="store_true")
p.add_argument("--vocals",action="store_true")
p.add_argument("--pdf",action="store_true")
a=p.parse_args()
result=run_local_audio(a.audio,out_dir=a.out,bpm=a.bpm,title=a.title,artist=a.artist,include_chords=not a.no_chords,separate_vocals=a.vocals,render_pdf=a.pdf)
print("MusicXML:",result.musicxml)
print("TRACK JSON:",result.score_data_path)
print("metadata:",result.meta_json)
print("PDF:",result.pdf or "not requested")
print("DRAFT ONLY — No TL charge, no TLD issuance. Review notes before publication.")
