from __future__ import annotations
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from auth_app.authentication import CookieJWTAuthentication
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
    """
    Loads a quiz by id and ensures it belongs to the requesting user.
    Raises 404 if quiz doesn't exist, 403 if it belongs to another user.
    """
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    if quiz.user_id != user.id:
        raise PermissionDenied("You do not have permission to access this quiz.")
    return quiz


def _get_attempt_or_403(attempt_id: int, user) -> QuizAttempt:
    """
    Loads an attempt by id and ensures it belongs to the requesting user.
    Raises 404 if attempt doesn't exist, 403 if it belongs to another user.
    """
    attempt = get_object_or_404(QuizAttempt, pk=attempt_id)
    if attempt.user_id != user.id:
        raise PermissionDenied("You do not have permission to access this attempt.")
    return attempt


def _recalculate_attempt_score(attempt: QuizAttempt) -> None:
    """
    Recomputes correct/total counters based on stored AttemptAnswer rows.
    Keeps total_questions stable if quiz has no questions for any reason.
    """
    correct = AttemptAnswer.objects.filter(attempt=attempt, is_correct=True).count()
    attempt.correct_count = correct
    attempt.total_questions = attempt.quiz.questions.count() or attempt.total_questions


class CreateQuizView(APIView):
    """
    Creates a quiz from a YouTube URL: download audio -> transcribe -> generate questions -> persist.
    Important: Force CookieJWTAuthentication to avoid SessionAuth+CSRF 403 in the frontend.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [CookieJWTAuthentication]

    def post(self, request):
        url = request.data.get("url")
        if not url:
            return Response({"detail": "Missing 'url'."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            quiz = create_quiz_for_user(user=request.user, url=url)
        except QuizlyValidationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(QuizCreateResponseSerializer(quiz).data, status=status.HTTP_201_CREATED)


class QuizListView(APIView):
    """
    Returns all quizzes belonging to the authenticated user (including questions).
    GET is safe, but we still require authentication.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [CookieJWTAuthentication]

    def get(self, request):
        quizzes = Quiz.objects.filter(user=request.user).prefetch_related("questions")
        return Response(
            QuizListSerializer(quizzes, many=True).data,
            status=status.HTTP_200_OK,
        )


class QuizDetailView(APIView):
    """
    Retrieve/update/delete a single quiz of the authenticated user.
    Patch/Delete are write operations; enforce CookieJWTAuthentication to avoid CSRF 403.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [CookieJWTAuthentication]

    def _get_quiz_or_403(self, request, quiz_id: int) -> Quiz:
        quiz = get_object_or_404(Quiz, pk=quiz_id)
        if quiz.user_id != request.user.id:
            raise PermissionDenied("You do not have permission to access this quiz.")
        return quiz

    def get(self, request, quiz_id: int):
        quiz = self._get_quiz_or_403(request, quiz_id)
        return Response(QuizDetailSerializer(quiz).data, status=status.HTTP_200_OK)

    def patch(self, request, quiz_id: int):
        quiz = self._get_quiz_or_403(request, quiz_id)

        serializer = QuizPatchSerializer(quiz, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(QuizDetailSerializer(quiz).data, status=status.HTTP_200_OK)

    def delete(self, request, quiz_id: int):
        quiz = self._get_quiz_or_403(request, quiz_id)
        quiz.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class StartAttemptView(APIView):
    """
    Starts a new attempt or returns an existing unfinished attempt unless 'new=true' is sent.
    Write operation => enforce CookieJWTAuthentication to avoid SessionAuth CSRF issues.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [CookieJWTAuthentication]

    def post(self, request, quiz_id: int):
        quiz = _get_quiz_or_403(quiz_id=quiz_id, user=request.user)

        data_in = StartAttemptInputSerializer(data=request.data)
        data_in.is_valid(raise_exception=True)
        force_new = data_in.validated_data["new"]

        if not force_new:
            existing = QuizAttempt.objects.filter(
                user=request.user, quiz=quiz, is_completed=False
            ).first()
            if existing:
                return Response(QuizAttemptSerializer(existing).data, status=status.HTTP_200_OK)

        attempt = QuizAttempt.objects.create(
            user=request.user,
            quiz=quiz,
            current_question_index=0,
            is_completed=False,
            total_questions=quiz.questions.count() or 10,
        )
        return Response(QuizAttemptSerializer(attempt).data, status=status.HTTP_201_CREATED)


class AttemptDetailView(APIView):
    """
    Returns attempt state + answers. Read-only endpoint.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, attempt_id: int):
        attempt = _get_attempt_or_403(attempt_id=attempt_id, user=request.user)
        attempt = (
            QuizAttempt.objects.filter(pk=attempt.pk)
            .select_related("quiz")
            .prefetch_related("answers", "quiz__questions")
            .get()
        )
        return Response(QuizAttemptSerializer(attempt).data, status=status.HTTP_200_OK)


class SaveAnswerView(APIView):
    """
    Saves/updates a selected option for a given question inside an attempt.
    Can also mark attempt as finished. Write operation => enforce CookieJWTAuthentication.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [CookieJWTAuthentication]

    @transaction.atomic
    def patch(self, request, attempt_id: int):
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
        return Response(QuizAttemptSerializer(attempt).data, status=status.HTTP_200_OK)


class FinishAttemptView(APIView):
    """
    Marks an attempt as completed and recalculates score. Write operation => enforce CookieJWTAuthentication.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [CookieJWTAuthentication]

    @transaction.atomic
    def post(self, request, attempt_id: int):
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
        return Response(QuizAttemptSerializer(attempt).data, status=status.HTTP_200_OK)


class AttemptResultView(APIView):
    """
    Returns result summary, optionally with per-question details.
    Read-only endpoint.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, attempt_id: int):
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
