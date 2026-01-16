from __future__ import annotations
import subprocess
from functools import lru_cache
import whisper
from .utils import QuizlyValidationError


def ensure_ffmpeg_available() -> None:
    """Raise if ffmpeg is not available on PATH."""
    try:
        subprocess.run(["ffmpeg", "-version"], check=True, capture_output=True, text=True)
    except Exception as exc:
        raise QuizlyValidationError("FFmpeg is not available. Please install ffmpeg and add it to PATH.") from exc


@lru_cache(maxsize=2)
def _get_model(model_name: str):
    """Load and cache a Whisper model."""
    return whisper.load_model(model_name)


def transcribe_audio(audio_path: str, model_name: str = "base") -> str:
    """
    Transcribe an audio file to plain text using Whisper.

    Args:
        audio_path: Path to the downloaded audio file.
        model_name: Whisper model name (e.g. "tiny", "base", "small").

    Returns:
        The transcript as a string.
    """
    if not audio_path:
        raise QuizlyValidationError("audio_path is required for transcription.")

    ensure_ffmpeg_available()
    model = _get_model(model_name)

    result = model.transcribe(audio_path)
    text = (result.get("text") or "").strip()

    if not text:
        raise QuizlyValidationError("Transcription produced empty text.")
    return text
