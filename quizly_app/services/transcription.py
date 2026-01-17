from __future__ import annotations
import subprocess
from functools import lru_cache
from typing import Any
from .utils import QuizlyValidationError


def ensure_ffmpeg_available() -> None:
    """Raise if ffmpeg is not available on PATH."""
    try:
        subprocess.run(["ffmpeg", "-version"], check=True, capture_output=True, text=True)
    except Exception as exc:
        raise QuizlyValidationError(
            "FFmpeg is not available. Please install ffmpeg and add it to PATH."
        ) from exc


def _import_whisper():
    """
    Import whisper lazily to avoid breaking Django startup when torch is not usable.
    """
    try:
        import whisper  
        return whisper
    except OSError as exc:
        raise QuizlyValidationError(
            "Whisper/PyTorch cannot be loaded on this system. "
            "On Windows this is often caused by missing VC++ runtime or a broken torch install."
        ) from exc
    except Exception as exc:
        raise QuizlyValidationError("Failed to import Whisper.") from exc


@lru_cache(maxsize=2)
def _get_model(model_name: str) -> Any:
    """Load and cache a Whisper model."""
    whisper = _import_whisper()
    return whisper.load_model(model_name)


def transcribe_audio(audio_path: str, model_name: str = "base") -> str:
    """
    Transcribe an audio file to plain text using Whisper.
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
