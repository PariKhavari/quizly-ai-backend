from __future__ import annotations
from rest_framework import serializers
from quizly_app.models import Quiz, Question, AttemptAnswer, QuizAttempt


class QuestionPublicSerializer(serializers.ModelSerializer):
    """Question output used for GET/PATCH quiz endpoints (no timestamps)."""

    class Meta:
        model = Question
        fields = ("id", "question_title", "question_options", "answer")
        read_only_fields = ("id",)


class QuestionCreateResponseSerializer(serializers.ModelSerializer):
    """Question output used for POST /api/createQuiz/ (includes timestamps)."""

    class Meta:
        model = Question
        fields = (
            "id",
            "question_title",
            "question_options",
            "answer",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class QuizListSerializer(serializers.ModelSerializer):
    """GET /api/quizzes/ response serializer."""
    questions = QuestionPublicSerializer(many=True, read_only=True)

    class Meta:
        model = Quiz
        fields = (
            "id",
            "title",
            "description",
            "created_at",
            "updated_at",
            "video_url",
            "questions",
        )
        read_only_fields = ("id", "created_at", "updated_at", "questions")


class QuizDetailSerializer(serializers.ModelSerializer):
    """GET /api/quizzes/{id}/ response serializer."""
    questions = QuestionPublicSerializer(many=True, read_only=True)

    class Meta:
        model = Quiz
        fields = (
            "id",
            "title",
            "description",
            "created_at",
            "updated_at",
            "video_url",
            "questions",
        )
        read_only_fields = ("id", "created_at", "updated_at", "questions")


class QuizCreateResponseSerializer(serializers.ModelSerializer):
    """POST /api/createQuiz/ response serializer (includes question timestamps)."""
    questions = QuestionCreateResponseSerializer(many=True, read_only=True)

    class Meta:
        model = Quiz
        fields = (
            "id",
            "title",
            "description",
            "created_at",
            "updated_at",
            "video_url",
            "questions",
        )
        read_only_fields = ("id", "created_at", "updated_at", "questions")


class QuizPatchSerializer(serializers.ModelSerializer):
    """PATCH input serializer for updating quiz title/description only."""

    class Meta:
        model = Quiz
        fields = ("title", "description")


class AttemptAnswerSerializer(serializers.ModelSerializer):
    """Stored answer for a quiz attempt."""
    question_id = serializers.IntegerField(source="question.id", read_only=True)

    class Meta:
        model = AttemptAnswer
        fields = (
            "id",
            "question_id",
            "selected_option",
            "is_correct",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "is_correct", "created_at", "updated_at")


class QuizAttemptSerializer(serializers.ModelSerializer):
    """Quiz attempt output including progress and answers."""
    quiz_id = serializers.IntegerField(source="quiz.id", read_only=True)
    score_percent = serializers.FloatField(read_only=True)
    answers = AttemptAnswerSerializer(many=True, read_only=True)

    class Meta:
        model = QuizAttempt
        fields = (
            "id",
            "quiz_id",
            "current_question_index",
            "is_completed",
            "correct_count",
            "total_questions",
            "score_percent",
            "started_at",
            "completed_at",
            "updated_at",
            "answers",
        )
        read_only_fields = (
            "id",
            "quiz_id",
            "correct_count",
            "total_questions",
            "score_percent",
            "started_at",
            "completed_at",
            "updated_at",
            "answers",
        )


class StartAttemptInputSerializer(serializers.Serializer):
    """Input for starting/restarting an attempt."""
    new = serializers.BooleanField(required=False, default=False)


class SaveAnswerInputSerializer(serializers.Serializer):
    """Input for saving/updating a selected answer and progress."""
    question_id = serializers.IntegerField()
    selected_option = serializers.CharField(max_length=255)
    current_question_index = serializers.IntegerField(required=False, min_value=0)
    finish = serializers.BooleanField(required=False, default=False)
