from __future__ import annotations
import os
from django.db import transaction
from quizly_app.models import Question, Quiz
from quizly_app.services.gemini import generate_quiz_from_transcript
from quizly_app.services.transcription import transcribe_audio
from quizly_app.services.utils import QuizlyValidationError, canonical_youtube_url, extract_youtube_video_id
from quizly_app.services.youtube import download_youtube_audio


def create_quiz_for_user(*, user, url: str, whisper_model: str = "base") -> Quiz:
    """
    Create a quiz for a user from a YouTube URL.
    Downloads audio, transcribes, generates quiz JSON, then saves to DB.
    """
    if not url:
        raise QuizlyValidationError("url is required.")

    video_id = extract_youtube_video_id(url)
    video_url = canonical_youtube_url(video_id)

    download = download_youtube_audio(video_url)

    try:
        transcript = transcribe_audio(download.audio_path, model_name=whisper_model)
        quiz_data = generate_quiz_from_transcript(transcript)

        with transaction.atomic():
            quiz = Quiz.objects.create(
                user=user,
                title=quiz_data["title"],
                description=quiz_data["description"],
                video_url=video_url,
            )

            Question.objects.bulk_create(
                [
                    Question(
                        quiz=quiz,
                        question_title=q["question_title"],
                        question_options=q["question_options"],
                        answer=q["answer"],
                    )
                    for q in quiz_data["questions"]
                ]
            )

        return quiz

    finally:
        try:
            if download.audio_path and os.path.exists(download.audio_path):
                os.remove(download.audio_path)
        except OSError:
            pass
