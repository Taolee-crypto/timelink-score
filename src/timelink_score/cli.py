"""CLI 진입점 — tlscore 명령."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from .pipeline import run_pipeline
from .score.render import find_musescore
from .tl3.header_parser import parse_header

app = typer.Typer(
    name="tlscore",
    help="TL3 음원 → 오선지 악보 자동 생성 (TimeLink 확장 모듈)",
    add_completion=False,
)
console = Console()


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


@app.command()
def header(
    tl3_path: Path = typer.Argument(..., help="TL3 파일 경로"),
) -> None:
    """TL3 헤더만 파싱해서 출력 (TL 소모 없음)."""
    try:
        h = parse_header(tl3_path)
    except Exception as e:
        console.print(f"[red]오류:[/red] {e}")
        raise typer.Exit(1)

    table = Table(title=f"TL3 헤더 — {tl3_path.name}")
    table.add_column("필드", style="cyan")
    table.add_column("값", style="white")

    table.add_row("version", f"0x{h.version:02X}")
    table.add_row("kind", h.kind)
    table.add_row("title", h.title)
    table.add_row("artist", h.artist)
    table.add_row("bpm", str(h.bpm))
    table.add_row("dur_sec", str(h.dur_sec))
    table.add_row("fs", str(h.sample_rate))
    table.add_row("ch", str(h.channels))
    table.add_row("fid", h.fid)
    table.add_row("N (segments)", str(h.num_segments))

    rights = h.rights
    if rights:
        table.add_row("creator_name", str(rights.get("creator_name", "")))
        table.add_row("isrc", str(rights.get("isrc", "")))
        table.add_row("copyright_year", str(rights.get("copyright_year", "")))
        table.add_row("country", str(rights.get("country", "")))

    console.print(table)


@app.command()
def doctor() -> None:
    """환경 점검 (MuseScore, 필수 패키지)."""
    table = Table(title="환경 점검")
    table.add_column("항목", style="cyan")
    table.add_column("상태", style="white")

    ms = find_musescore()
    table.add_row("MuseScore CLI", ms or "[red]미설치[/red]")

    for pkg in ("librosa", "soundfile", "music21", "httpx", "numpy"):
        try:
            __import__(pkg)
            table.add_row(pkg, "[green]OK[/green]")
        except ImportError:
            table.add_row(pkg, "[red]미설치[/red]")

    for pkg in ("demucs", "basic_pitch"):
        try:
            __import__(pkg)
            table.add_row(pkg, "[green]OK[/green]")
        except ImportError:
            table.add_row(pkg, "[yellow]미설치 (선택)[/yellow]")

    console.print(table)


@app.command("local")
def local_audio(
    audio_path: Path = typer.Argument(..., help="직접 제작하거나 분석 권한을 가진 음원 WAV/MP3/FLAC"),
    out_dir: Path = typer.Option(Path("output"), "--out", "-o"),
    title: str = typer.Option("", "--title", help="악보 제목"),
    artist: str = typer.Option("", "--artist", help="아티스트"),
    bpm: float = typer.Option(120, "--bpm", help="원곡 BPM (수동 확인)"),
    chords: bool = typer.Option(True, "--chords/--no-chords"),
    vocals: bool = typer.Option(False, "--vocals/--no-vocals", help="선택: Demucs 보컬 분리"),
    pdf: bool = typer.Option(False, "--pdf/--no-pdf", help="선택: LilyPond PDF"),
) -> None:
    """권한이 있는 로컬 음원을 멜로디·코드·MusicXML·TRACK JSON으로 분석.

    이 명령은 V5 암호화 재생 데이터를 가져오지 않으며 TL을 차감하지 않습니다.
    """
    from .pipeline import run_local_audio

    try:
        result = run_local_audio(
            audio_path, out_dir=out_dir, title=title, artist=artist,
            bpm=bpm, include_chords=chords, separate_vocals=vocals,
            render_pdf=pdf,
        )
    except Exception as exc:
        console.print(f"[red]분석 실패:[/red] {exc}")
        raise typer.Exit(1) from exc

    console.print(f"[green]MusicXML 초안:[/green] {result.musicxml}")
    console.print(f"[green]TRACK 악보 JSON:[/green] {result.score_data_path}")
    console.print(f"[green]분석 메타데이터:[/green] {result.meta_json}")
    if result.pdf:
        console.print(f"[green]PDF 악보:[/green] {result.pdf}")
    console.print("[yellow]초안은 수동 검수가 필요하며 TLD 발행이나 TL 과금은 진행되지 않았습니다.[/yellow]")


@app.command()
def run(
    tl3_path: Path = typer.Argument(..., help="TL3 파일 경로"),
    out_dir: Path = typer.Option("output", "--out", "-o", help="산출물 폴더"),
    server_base: str = typer.Option(
        ..., "--server", envvar="TL_SERVER_BASE", help="TL 서버 베이스 URL"
    ),
    session_id: str = typer.Option(
        ..., "--session", envvar="TL_SESSION_ID", help="TL 세션 ID"
    ),
    auth_token: Optional[str] = typer.Option(
        None, "--token", envvar="TL_AUTH_TOKEN", help="인증 토큰"
    ),
    time_signature: str = typer.Option("4/4", "--ts", help="박자표"),
    quantize_grid: str = typer.Option("16th", "--grid", help="양자화 그리드"),
    skip_vocals: bool = typer.Option(
        False, "--skip-vocals", help="Demucs 보컬 분리 생략"
    ),
    skip_pdf: bool = typer.Option(False, "--skip-pdf", help="PDF 렌더링 생략"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="상세 로그"),
) -> None:
    """TL3 → 악보 PDF 전체 파이프라인."""
    _setup_logging(verbose)

    if not tl3_path.exists():
        console.print(f"[red]파일 없음:[/red] {tl3_path}")
        raise typer.Exit(1)

    console.print(f"[bold]TL3:[/bold] {tl3_path}")
    console.print(f"[bold]출력:[/bold] {out_dir}")
    console.print("[yellow]⚠️  세그먼트 요청 시 TL이 차감됩니다.[/yellow]")

    try:
        result = run_pipeline(
            tl3_path,
            out_dir=out_dir,
            server_base=server_base,
            session_id=session_id,
            auth_token=auth_token,
            time_signature=time_signature,
            quantize_grid=quantize_grid,
            skip_vocal_separation=skip_vocals,
            skip_pdf=skip_pdf,
        )
    except Exception as e:
        console.print(f"[red]파이프라인 실패:[/red] {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)

    table = Table(title="✅ 완료")
    table.add_column("산출물", style="cyan")
    table.add_column("경로", style="white")
    if result.musicxml:
        table.add_row("MusicXML", str(result.musicxml))
    if result.pdf:
        table.add_row("PDF", str(result.pdf))
    if result.meta_json:
        table.add_row("meta.json", str(result.meta_json))
    if result.key_result:
        table.add_row(
            "조성",
            f"{result.key_result.korean} "
            f"({result.key_result.signature_str}, "
            f"신뢰도 {result.key_result.confidence:.2f})",
        )
    console.print(table)


if __name__ == "__main__":
    app()
