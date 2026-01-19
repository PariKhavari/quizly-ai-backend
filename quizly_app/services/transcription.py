from __future__ import annotations
import os
from dataclasses import dataclass
from typing import Any
import numpy as np
import whisper
from quizly_app.services.utils import QuizlyValidationError


@dataclass(frozen=True)
class TranscriptionResult:
    text: str
    raw: dict[str, Any]


def transcribe_audio(audio_path: str, model_name: str = "base") -> str:
    """
    Transcribe an audio file using Whisper.

    This function validates that the audio can be decoded into samples.
    If decoding fails (or yields empty audio), we raise a validation error
    so the API can return a 4xx instead of crashing with a 500.
    """
    _ensure_audio_file_exists(audio_path)

    try:
        audio = whisper.load_audio(audio_path)
    except Exception as exc:
        raise QuizlyValidationError("Audio could not be decoded. Ensure FFmpeg is installed and the file contains audio.") from exc

    if not isinstance(audio, np.ndarray) or audio.size == 0:
        raise QuizlyValidationError("Audio is empty or unreadable. Please try a different YouTube video.")

    try:
        model = whisper.load_model(model_name)
        result = model.transcribe(audio_path)
    except RuntimeError as exc:
        raise QuizlyValidationError("Whisper failed to transcribe the audio. The audio may be empty or unsupported.") from exc
    except Exception as exc:
        raise QuizlyValidationError("Unexpected error while transcribing audio.") from exc

    text = (result.get("text") or "").strip()
    if not text:
        raise QuizlyValidationError("Transcription result is empty. Please try a different YouTube video.")

    return text


def _ensure_audio_file_exists(path: str) -> None:
    if not path or not os.path.exists(path):
        raise QuizlyValidationError("Audio file not found. Please try again.")
    if os.path.getsize(path) == 0:
        raise QuizlyValidationError("Audio file is empty. Please try again.")
