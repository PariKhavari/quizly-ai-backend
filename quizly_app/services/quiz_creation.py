from __future__ import annotations
from django.db import transaction
from quizly_app.models import Question, Quiz
from quizly_app.services.gemini import generate_quiz_from_transcript
from quizly_app.services.transcription import transcribe_audio
from quizly_app.services.utils import QuizlyValidationError
from quizly_app.services.youtube import download_youtube_audio


@transaction.atomic
def create_quiz_for_user(user, url: str, whisper_model: str = "base") -> Quiz:
    """
    End-to-end pipeline:
    - download YouTube audio
    - transcribe via Whisper
    - generate quiz via Gemini
    - persist Quiz + Questions
    """
    download = download_youtube_audio(url)

    try:
        transcript = transcribe_audio(download.audio_path, model_name=whisper_model)
        quiz_data = generate_quiz_from_transcript(transcript)
    except QuizlyValidationError:
        raise
    except Exception as exc:
        raise QuizlyValidationError("Quiz creation failed unexpectedly. Please try again.") from exc

    quiz = Quiz.objects.create(
        user=user,
        title=quiz_data["title"],
        description=quiz_data["description"],
        video_url=download.video_url,
    )

    questions = []
    for q in quiz_data["questions"]:
        questions.append(
            Question(
                quiz=quiz,
                question_title=q["question_title"],
                question_options=q["question_options"],
                answer=q["answer"],
            )
        )

    Question.objects.bulk_create(questions)
    return quiz
