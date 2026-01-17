from __future__ import annotations
from rest_framework import serializers
from quizly_app.models import Quiz, Question


class QuestionSerializer(serializers.ModelSerializer):
    """Question representation for nested quiz responses."""

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


class QuizSerializer(serializers.ModelSerializer):
    """Quiz representation including nested questions."""

    questions = QuestionSerializer(many=True, read_only=True)

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
        read_only_fields = ("id", "created_at", "updated_at", "video_url", "questions")


class QuizUpdateSerializer(serializers.ModelSerializer):
    """Allows partial updates for title/description only."""

    class Meta:
        model = Quiz
        fields = ("title", "description")


class CreateQuizSerializer(serializers.Serializer):
    """Request serializer for creating a quiz from a YouTube URL."""

    url = serializers.URLField()
