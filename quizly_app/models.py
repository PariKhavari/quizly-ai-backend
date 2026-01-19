from __future__ import annotations
from django.conf import settings
from django.db import models
from django.utils import timezone


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
    """
    A single "playthrough" of a quiz by a user.

    Why this exists:
    - One user can replay the same quiz multiple times.
    - We can persist progress (current question) and store answers.
    - We can compute a score at the end.
    """

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

    current_question_index = models.PositiveIntegerField(default=0)
    is_completed = models.BooleanField(default=False)
    correct_count = models.PositiveIntegerField(default=0)
    total_questions = models.PositiveIntegerField(default=10)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["user", "quiz", "is_completed"]),
        ]

    def __str__(self) -> str:
        return f"Attempt #{self.pk} (Quiz #{self.quiz_id}, User #{self.user_id})"

    def mark_completed(self) -> None:
        """Mark the attempt as completed and set completion timestamp."""
        self.is_completed = True
        self.completed_at = timezone.now()

    @property
    def score_percent(self) -> float:
        """Return the score as a percentage (0..100)."""
        if not self.total_questions:
            return 0.0
        return round((self.correct_count / self.total_questions) * 100.0, 1)


class AttemptAnswer(models.Model):
    """
    The user's selected answer for a specific question in a specific attempt.

    Design:
    - Unique per (attempt, question), so changing an answer updates the same row.
    - Stores 'is_correct' for quick score computation.
    """

    attempt = models.ForeignKey(
        QuizAttempt,
        on_delete=models.CASCADE,
        related_name="answers",
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="attempt_answers",
    )

    selected_option = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["attempt", "question"],
                name="uniq_attempt_question",
            )
        ]
        indexes = [
            models.Index(fields=["attempt", "question"]),
        ]

    def __str__(self) -> str:
        return f"AttemptAnswer (Attempt #{self.attempt_id}, Question #{self.question_id})"