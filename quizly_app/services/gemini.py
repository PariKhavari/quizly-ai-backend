from __future__ import annotations
import json
import os
import time
from functools import lru_cache
from typing import Any, Dict, Optional
from google import genai
from google.genai.errors import ClientError
from .utils import QuizlyValidationError, parse_ai_quiz_json, validate_quiz_schema


def build_quiz_prompt(transcript: str) -> str:
    """Build a strict JSON-only prompt for quiz generation."""
    if not transcript or not transcript.strip():
        raise QuizlyValidationError("Transcript is empty.")

    return (
        "Generate a quiz as VALID JSON only.\n"
        "Return exactly ONE JSON object and nothing else.\n\n"
        "Schema:\n"
        "{\n"
        '  "title": "string",\n'
        '  "description": "string (<= 150 characters)",\n'
        '  "questions": [\n'
        "    {\n"
        '      "question_title": "string",\n'
        '      "question_options": ["string", "string", "string", "string"],\n'
        '      "answer": "string (must be one of question_options)"\n'
        "    }\n"
        "  ]\n"
        "}\n\n"
        "Hard rules:\n"
        "- Output MUST be parsable with json.loads().\n"
        "- questions MUST contain EXACTLY 10 items.\n"
        "- Each question_options MUST contain EXACTLY 4 DISTINCT strings.\n"
        "- Do NOT include markdown, code fences, comments, ellipsis '...', or extra text.\n\n"
        "Transcript:\n"
        f"{transcript.strip()}\n"
    )


def build_fix_prompt(broken_quiz: Dict[str, Any]) -> str:
    """Ask the model to repair the JSON to match the strict schema."""
    return (
        "Fix the following JSON to match these rules and return VALID JSON only:\n"
        "- Root object must contain: title, description, questions\n"
        "- questions MUST contain EXACTLY 10 items\n"
        "- Each item must contain: question_title, question_options (exactly 4 distinct strings), answer\n"
        "- answer MUST be one of question_options\n"
        "- Remove any extra keys, markdown, comments, and ellipsis\n\n"
        "JSON to fix:\n"
        f"{json.dumps(broken_quiz, ensure_ascii=False)}\n"
    )


@lru_cache(maxsize=1)
def _get_client() -> genai.Client:
    """
    Create and cache a single Gemini client for the process.

    Caching avoids 'httpx client has been closed' errors that can happen when the
    SDK retries internally while a short-lived client gets garbage-collected.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise QuizlyValidationError("GEMINI_API_KEY is missing.")
    return genai.Client(api_key=api_key)


def _call_gemini(prompt: str, model: str) -> str:
    """Call Gemini and return the response text."""
    client = _get_client()
    response = client.models.generate_content(model=model, contents=prompt)
    return (response.text or "").strip()


def generate_quiz_from_transcript(
    transcript: str,
    model: str = "gemini-2.5-flash",
    max_attempts: int = 3,
) -> Dict[str, Any]:
    """
    Generate and validate quiz JSON from a transcript using Gemini.

    Flow:
    1) Generate JSON from transcript
    2) Validate
    3) If schema fails (often question count), run one repair call and validate again
    4) Retry the whole process a few times if needed
    """
    base_prompt = build_quiz_prompt(transcript)
    last_error: Optional[Exception] = None

    for attempt in range(1, max_attempts + 1):
        try:
            raw_text = _call_gemini(base_prompt, model=model)
            if not raw_text:
                raise QuizlyValidationError("Gemini returned empty output.")

            data = parse_ai_quiz_json(raw_text)

            try:
                return validate_quiz_schema(data)
            except QuizlyValidationError:
                fixed_prompt = build_fix_prompt(data)
                fixed_raw = _call_gemini(fixed_prompt, model=model)
                fixed_data = parse_ai_quiz_json(fixed_raw)
                return validate_quiz_schema(fixed_data)

        except ClientError as exc:
            last_error = exc
            status_code = getattr(exc, "status_code", None)

            if status_code == 429:
                raise QuizlyValidationError(
                    "Gemini quota/rate limit exceeded (HTTP 429). Try again later."
                ) from exc

            raise QuizlyValidationError(f"Gemini request failed (HTTP {status_code}).") from exc

        except QuizlyValidationError as exc:
            last_error = exc
            if attempt < max_attempts:
                time.sleep(1.0)
                continue
            raise

        except Exception as exc:
            last_error = exc
            raise QuizlyValidationError("Unexpected error while calling Gemini.") from exc

    raise QuizlyValidationError("Gemini request failed.") from last_error
