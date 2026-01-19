from __future__ import annotations
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from quizly_app.services.utils import QuizlyValidationError
from quizly_app.api.serializers import (
    QuizAttemptSerializer,
    QuizCreateResponseSerializer,
    QuizListSerializer,
    QuizPatchSerializer,
    SaveAnswerInputSerializer,
    StartAttemptInputSerializer,
    QuizDetailSerializer,
)
from quizly_app.models import AttemptAnswer, Question, Quiz, QuizAttempt
from quizly_app.services.quiz_creation import create_quiz_for_user


def _get_quiz_or_403(quiz_id: int, user) -> Quiz:
    """Return the quiz if owned by user; otherwise raise 403 (or 404 if missing)."""
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    if quiz.user_id != user.id:
        raise PermissionDenied("You do not have permission to access this quiz.")
    return quiz


def _get_attempt_or_403(attempt_id: int, user) -> QuizAttempt:
    """Return the attempt if owned by user; otherwise raise 403 (or 404 if missing)."""
    attempt = get_object_or_404(QuizAttempt, pk=attempt_id)
    if attempt.user_id != user.id:
        raise PermissionDenied("You do not have permission to access this attempt.")
    return attempt


def _recalculate_attempt_score(attempt: QuizAttempt) -> None:
    """Update attempt.correct_count and attempt.total_questions based on stored answers."""
    correct = AttemptAnswer.objects.filter(attempt=attempt, is_correct=True).count()
    attempt.correct_count = correct
    attempt.total_questions = attempt.quiz.questions.count() or attempt.total_questions


class CreateQuizView(APIView):
    """Create a quiz from a YouTube URL and persist it with generated questions."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Create a quiz for the authenticated user from request.data['url']."""
        url = request.data.get("url")
        if not url:
            return Response(
                {"detail": "Missing 'url'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            quiz = create_quiz_for_user(user=request.user, url=url)
        except QuizlyValidationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            QuizCreateResponseSerializer(quiz).data,
            status=status.HTTP_201_CREATED,
        )


class QuizListView(APIView):
    """List all quizzes belonging to the authenticated user."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Return all quizzes owned by the authenticated user."""
        quizzes = Quiz.objects.filter(user=request.user).prefetch_related("questions")
        return Response(
            QuizListSerializer(quizzes, many=True).data,
            status=status.HTTP_200_OK,
        )


class QuizDetailView(APIView):
    """Retrieve, update, or delete a single quiz owned by the authenticated user."""
    permission_classes = [IsAuthenticated]

    def _get_quiz_or_403(self, request, quiz_id: int) -> Quiz:
        """Return the quiz if owned by request.user; otherwise raise 403."""
        quiz = get_object_or_404(Quiz, pk=quiz_id)
        if quiz.user_id != request.user.id:
            raise PermissionDenied("You do not have permission to access this quiz.")
        return quiz

    def get(self, request, quiz_id: int):
        """Return full quiz detail (including questions) for the given quiz_id."""
        quiz = self._get_quiz_or_403(request, quiz_id)
        return Response(
            QuizDetailSerializer(quiz).data,
            status=status.HTTP_200_OK,
        )

    def patch(self, request, quiz_id: int):
        """Partially update quiz fields (title/description) for the given quiz_id."""
        quiz = self._get_quiz_or_403(request, quiz_id)

        serializer = QuizPatchSerializer(quiz, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            QuizDetailSerializer(quiz).data,
            status=status.HTTP_200_OK,
        )

    def delete(self, request, quiz_id: int):
        """Delete the quiz (and all related questions) for the given quiz_id."""
        quiz = self._get_quiz_or_403(request, quiz_id)
        quiz.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class StartAttemptView(APIView):
    """Start a new attempt or resume an existing unfinished attempt for a quiz."""
    permission_classes = [IsAuthenticated]

    def post(self, request, quiz_id: int):
        """Start/resume an attempt for quiz_id; pass {'new': true} to force a new attempt."""
        quiz = _get_quiz_or_403(quiz_id=quiz_id, user=request.user)

        data_in = StartAttemptInputSerializer(data=request.data)
        data_in.is_valid(raise_exception=True)
        force_new = data_in.validated_data["new"]

        if not force_new:
            existing = QuizAttempt.objects.filter(
                user=request.user,
                quiz=quiz,
                is_completed=False,
            ).first()
            if existing:
                return Response(
                    QuizAttemptSerializer(existing).data,
                    status=status.HTTP_200_OK,
                )

        attempt = QuizAttempt.objects.create(
            user=request.user,
            quiz=quiz,
            current_question_index=0,
            is_completed=False,
            total_questions=quiz.questions.count() or 10,
        )
        return Response(
            QuizAttemptSerializer(attempt).data,
            status=status.HTTP_201_CREATED,
        )


class AttemptDetailView(APIView):
    """Retrieve the current state of an attempt including saved answers."""
    permission_classes = [IsAuthenticated]

    def get(self, request, attempt_id: int):
        """Return attempt details for attempt_id if owned by the authenticated user."""
        attempt = _get_attempt_or_403(attempt_id=attempt_id, user=request.user)
        attempt = (
            QuizAttempt.objects.filter(pk=attempt.pk)
            .select_related("quiz")
            .prefetch_related("answers", "quiz__questions")
            .get()
        )
        return Response(
            QuizAttemptSerializer(attempt).data,
            status=status.HTTP_200_OK,
        )


class SaveAnswerView(APIView):
    """Save/update an answer for an attempt and optionally mark the attempt as finished."""
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def patch(self, request, attempt_id: int):
        """Upsert an answer for attempt_id and update progress/score; supports finish=true."""
        attempt = _get_attempt_or_403(attempt_id=attempt_id, user=request.user)

        payload = SaveAnswerInputSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        question_id = payload.validated_data["question_id"]
        selected_option = payload.validated_data["selected_option"]
        finish = payload.validated_data.get("finish", False)

        question = get_object_or_404(Question, pk=question_id)

        if question.quiz_id != attempt.quiz_id:
            raise ValidationError("Question does not belong to this quiz.")

        options = question.question_options or []
        if selected_option not in options:
            raise ValidationError("Selected option must be one of question_options.")

        is_correct = selected_option == question.answer

        AttemptAnswer.objects.update_or_create(
            attempt=attempt,
            question=question,
            defaults={"selected_option": selected_option, "is_correct": is_correct},
        )

        if "current_question_index" in payload.validated_data:
            attempt.current_question_index = payload.validated_data["current_question_index"]

        _recalculate_attempt_score(attempt)

        if finish and not attempt.is_completed:
            attempt.mark_completed()

        attempt.save()

        attempt = (
            QuizAttempt.objects.filter(pk=attempt.pk)
            .select_related("quiz")
            .prefetch_related("answers")
            .get()
        )
        return Response(
            QuizAttemptSerializer(attempt).data,
            status=status.HTTP_200_OK,
        )


class FinishAttemptView(APIView):
    """Finalize an attempt by marking it completed and returning its final state."""
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, attempt_id: int):
        """Mark attempt_id as completed and return updated attempt data."""
        attempt = _get_attempt_or_403(attempt_id=attempt_id, user=request.user)

        _recalculate_attempt_score(attempt)
        if not attempt.is_completed:
            attempt.mark_completed()
        attempt.save()

        attempt = (
            QuizAttempt.objects.filter(pk=attempt.pk)
            .select_related("quiz")
            .prefetch_related("answers")
            .get()
        )
        return Response(
            QuizAttemptSerializer(attempt).data,
            status=status.HTTP_200_OK,
        )


class AttemptResultView(APIView):
    """Return result summary and optionally per-question breakdown for an attempt."""
    permission_classes = [IsAuthenticated]

    def get(self, request, attempt_id: int):
        """Return attempt result; add ?details=1 to include per-question answer comparison."""
        attempt = _get_attempt_or_403(attempt_id=attempt_id, user=request.user)
        attempt = (
            QuizAttempt.objects.filter(pk=attempt.pk)
            .select_related("quiz")
            .prefetch_related("answers", "quiz__questions")
            .get()
        )

        _recalculate_attempt_score(attempt)
        attempt.save(update_fields=["correct_count", "total_questions", "updated_at"])

        include_details = request.query_params.get("details") in ("1", "true", "True")

        result = {
            "attempt_id": attempt.id,
            "quiz_id": attempt.quiz_id,
            "correct": attempt.correct_count,
            "total": attempt.total_questions,
            "percent": attempt.score_percent,
            "is_completed": attempt.is_completed,
        }

        if include_details:
            answer_map = {a.question_id: a for a in attempt.answers.all()}
            details = []

            for q in attempt.quiz.questions.all().order_by("id"):
                a = answer_map.get(q.id)
                details.append(
                    {
                        "question_id": q.id,
                        "question_title": q.question_title,
                        "question_options": q.question_options,
                        "correct_answer": q.answer,
                        "selected_option": a.selected_option if a else None,
                        "is_correct": a.is_correct if a else False,
                    }
                )
            result["details"] = details

        return Response(result, status=status.HTTP_200_OK)
