"""Offline development operator test, not an end-user manual-upload workflow.

A trusted GPU inference worker must later retrieve the licensed V5 source by
authenticated file_id and pass its registered lyrics here.
"""
import argparse
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"src"))
from timelink_score.vocal_score import create_vocal_lyric_score

def main():
    parser=argparse.ArgumentParser(description="TILO singer-melody + registered lyrics only (review draft)")
    parser.add_argument("source_audio",help="Authorized local test source, not a user upload")
    parser.add_argument("--lyrics-file",required=True,help="UTF-8 lyrics already registered with the song")
    parser.add_argument("--title",required=True)
    parser.add_argument("--artist",default="")
    parser.add_argument("--bpm",type=float,required=True)
    parser.add_argument("--language",default="ko")
    parser.add_argument("--device",default="cpu",choices=["cpu","cuda"])
    parser.add_argument("--out",required=True)
    args=parser.parse_args()
    lyrics=Path(args.lyrics_file).read_text(encoding="utf-8")
    result=create_vocal_lyric_score(args.source_audio,lyrics,out_dir=args.out,
                                   title=args.title,artist=args.artist,bpm=args.bpm,
                                   device=args.device,language=args.language)
    print("VOCAL MUSICXML:",result["musicxml"])
    print("TRACK DRAFT JSON:",result["score_json"])
    print("STATUS: Review-only. No TLD issued or TL charged.")
if __name__=="__main__":
    main()
