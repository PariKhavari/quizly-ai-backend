from __future__ import annotations
import json
import re
from typing import Any, Dict, List
from urllib.parse import parse_qs, urlparse


class QuizlyValidationError(ValueError):
    """Raised when inputs or AI outputs do not match the expected format."""


_YOUTUBE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


def extract_youtube_video_id(url: str) -> str:
    """Extract a YouTube video ID from common URL formats."""
    if not url or not isinstance(url, str):
        raise QuizlyValidationError("URL is missing or invalid.")

    parsed = urlparse(url.strip())
    host = (parsed.hostname or "").lower()
    path = parsed.path.strip("/")

    video_id = ""

    if "youtube.com" in host:
        qs = parse_qs(parsed.query)
        if qs.get("v"):
            video_id = (qs["v"][0] or "").strip()

        if not video_id and path.startswith("shorts/"):
            video_id = (path.split("/", 1)[1] or "").strip()

        if not video_id and path.startswith("embed/"):
            video_id = (path.split("/", 1)[1] or "").strip()

    if not video_id and "youtu.be" in host:
        if path:
            video_id = (path.split("/", 1)[0] or "").strip()

    if not video_id or not _YOUTUBE_ID_RE.match(video_id):
        raise QuizlyValidationError("Could not extract a valid YouTube video ID.")

    return video_id


def canonical_youtube_url(video_id: str) -> str:
    """Return canonical URL format required by the mentor: https://www.youtube.com/watch?v=VIDEO_ID"""
    if not video_id or not _YOUTUBE_ID_RE.match(video_id):
        raise QuizlyValidationError("Invalid video ID.")
    return f"https://www.youtube.com/watch?v={video_id}"


def strip_markdown_fences(text: str) -> str:
    """Remove common Markdown code fences like ```json ... ``` or ``` ... ```."""
    if text is None:
        return ""
    cleaned = text.strip()
    cleaned = re.sub(r"^\s*```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```\s*$", "", cleaned)
    return cleaned.strip()


def extract_json_object(text: str) -> str:
    """Extract JSON object by slicing from first '{' to last '}'."""
    cleaned = strip_markdown_fences(text)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise QuizlyValidationError("No JSON object found in AI output.")
    return cleaned[start : end + 1].strip()


def parse_ai_quiz_json(raw_text: str) -> Dict[str, Any]:
    """Parse AI output into a Python dict (expects a JSON object)."""
    json_text = extract_json_object(raw_text)
    try:
        data = json.loads(json_text)
    except json.JSONDecodeError as exc:
        raise QuizlyValidationError(f"AI output JSON is not parsable: {exc}") from exc

    if not isinstance(data, dict):
        raise QuizlyValidationError("AI output root must be a JSON object.")
    return data


def validate_quiz_schema(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate quiz schema (10 questions, 4 options each, answer in options)."""
    title = str(data.get("title", "")).strip()
    description = str(data.get("description", "")).strip()
    questions = data.get("questions")

    if not title:
        raise QuizlyValidationError("Quiz title is missing.")
    if not description:
        raise QuizlyValidationError("Quiz description is missing.")
    if not isinstance(questions, list):
        raise QuizlyValidationError("'questions' must be a list.")
    if len(questions) != 10:
        raise QuizlyValidationError("AI must generate exactly 10 questions.")

    cleaned_questions: List[Dict[str, Any]] = []
    for idx, q in enumerate(questions, start=1):
        if not isinstance(q, dict):
            raise QuizlyValidationError(f"Question {idx}: must be an object.")

        q_title = str(q.get("question_title", "")).strip()
        options = q.get("question_options")
        answer = str(q.get("answer", "")).strip()

        if not q_title:
            raise QuizlyValidationError(f"Question {idx}: question_title is missing.")
        if not isinstance(options, list) or len(options) != 4:
            raise QuizlyValidationError(f"Question {idx}: must have exactly 4 options.")

        cleaned_options = [str(opt).strip() for opt in options]
        if any(not opt for opt in cleaned_options):
            raise QuizlyValidationError(f"Question {idx}: empty option found.")
        if len(set(cleaned_options)) != 4:
            raise QuizlyValidationError(f"Question {idx}: options must be distinct.")
        if answer not in cleaned_options:
            raise QuizlyValidationError(f"Question {idx}: answer must be one of the options.")

        cleaned_questions.append(
            {
                "question_title": q_title,
                "question_options": cleaned_options,
                "answer": answer,
            }
        )

    return {
        "title": title,
        "description": description,
        "questions": cleaned_questions,
    }


def build_yt_dlp_options(tmp_filename: str) -> Dict[str, Any]:
    """Return yt-dlp options as required by the mentor."""
    if not tmp_filename:
        raise QuizlyValidationError("tmp_filename is required for yt-dlp options.")

    return {
        "format": "bestaudio/best",
        "outtmpl": tmp_filename,
        "quiet": True,
        "noplaylist": True,
    }
