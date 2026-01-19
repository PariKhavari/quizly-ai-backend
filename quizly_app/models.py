from __future__ import annotations
from django.conf import settings
from django.db import models


class Quiz(models.Model):
    """A quiz generated from a YouTube video for a specific user."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="quizzes",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    video_url = models.URLField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.title} (#{self.pk})"


class Question(models.Model):
    """A single question belonging to a quiz."""

    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name="questions",
    )
    question_title = models.TextField()
    question_options = models.JSONField(default=list)
    answer = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:
        return f"Question #{self.pk} (Quiz #{self.quiz_id})"


class QuizAttempt(models.Model):
    """A user's playthrough of a quiz (progress + completion)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="quiz_attempts",
    )
    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name="attempts",
    )
    current_index = models.PositiveIntegerField(default=0)
    is_finished = models.BooleanField(default=False)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["user", "quiz", "is_finished"]),
        ]

    def __str__(self) -> str:
        return f"Attempt #{self.pk} (User #{self.user_id}, Quiz #{self.quiz_id})"


class UserAnswer(models.Model):
    """A stored answer for a question within an attempt (can be updated)."""

    attempt = models.ForeignKey(
        QuizAttempt,
        on_delete=models.CASCADE,
        related_name="answers",
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="user_answers",
    )
    selected_option = models.CharField(max_length=255)
    answered_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("attempt", "question")
        indexes = [
            models.Index(fields=["attempt", "question"]),
        ]

    def __str__(self) -> str:
        return f"Answer (Attempt #{self.attempt_id}, Question #{self.question_id})"