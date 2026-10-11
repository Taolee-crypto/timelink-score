"""Basic Pitch으로 피치 + 온셋 → MIDI.

원칙 3 준수: basic-pitch는 외부 ML 모델. 결과 MIDI는 임시 산출물.
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class PitchExtractionError(Exception):
    """피치 추출 실패."""


def extract_midi(
    audio_path: str | Path,
    out_dir: str | Path,
    *,
    onset_threshold: float = 0.5,
    frame_threshold: float = 0.3,
    minimum_note_length_ms: float = 58.0,
    minimum_frequency: float | None = None,
    maximum_frequency: float | None = None,
    multiple_pitch_bends: bool = False,
    melodia_trick: bool = True,
    save_midi: bool = True,
) -> Path:
    """Basic Pitch으로 오디오에서 MIDI를 생성."""
    try:
        from basic_pitch import ICASSP_2022_MODEL_PATH
        from basic_pitch.inference import predict_and_save
    except ImportError as e:
        raise PitchExtractionError(
            "basic-pitch가 설치되어 있지 않습니다. "
            "`pip install basic-pitch` 후 다시 시도하세요."
        ) from e

    audio_path = Path(audio_path).resolve()
    if not audio_path.exists():
        raise PitchExtractionError(f"입력 오디오가 없습니다: {audio_path}")

    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        predict_and_save(
            audio_path_list=[str(audio_path)],
            output_directory=str(out_dir),
            save_midi=save_midi,
            sonify_midi=False,
            save_model_outputs=False,
            save_notes=False,
            model_or_model_path=ICASSP_2022_MODEL_PATH,
            onset_threshold=onset_threshold,
            frame_threshold=frame_threshold,
            minimum_note_length=minimum_note_length_ms,
            minimum_frequency=minimum_frequency,
            maximum_frequency=maximum_frequency,
            multiple_pitch_bends=multiple_pitch_bends,
            melodia_trick=melodia_trick,
        )
    except Exception as e:
        raise PitchExtractionError(f"basic-pitch 추론 실패: {e}") from e

    midi_path = out_dir / f"{audio_path.stem}_basic_pitch.mid"
    if not midi_path.exists():
        candidates = list(out_dir.glob("*.mid")) + list(out_dir.glob("*.midi"))
        if not candidates:
            raise PitchExtractionError(
                f"MIDI 결과를 찾을 수 없습니다. out_dir={out_dir}"
            )
        midi_path = candidates[0]

    logger.info("MIDI 생성: %s", midi_path)
    return midi_path
