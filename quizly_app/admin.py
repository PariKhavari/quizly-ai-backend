from __future__ import annotations
from django.contrib import admin
from quizly_app.models import Quiz, Question, QuizAttempt, AttemptAnswer


class QuestionInline(admin.TabularInline):
    """Fragen direkt im Quiz-Admin bearbeiten/ansehen (Inline)."""

    model = Question
    extra = 0
    fields = ("question_title", "answer", "question_options", "created_at", "updated_at")
    readonly_fields = ("created_at", "updated_at")
    show_change_link = True


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    """Admin-Ansicht für Quizzes inkl. Inline-Fragen."""

    list_display = ("id", "title", "user", "created_at", "updated_at")
    list_select_related = ("user",)
    list_filter = ("created_at", "updated_at")
    search_fields = ("title", "description", "video_url", "user__username", "user__email")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")
    inlines = (QuestionInline,)


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    """Admin-Ansicht für einzelne Fragen."""

    list_display = ("id", "quiz", "question_title", "created_at")
    list_select_related = ("quiz",)
    list_filter = ("created_at",)
    search_fields = ("question_title", "answer", "quiz__title")
    ordering = ("id",)


class AttemptAnswerInline(admin.TabularInline):
    """Antworten direkt im Attempt-Admin als Inline anzeigen."""

    model = AttemptAnswer
    extra = 0
    fields = ("question", "selected_option", "is_correct", "created_at", "updated_at")
    readonly_fields = ("is_correct", "created_at", "updated_at")
    show_change_link = True


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    """Admin-Ansicht für Quiz-Versuche inkl. Inline-Antworten."""

    list_display = ("id", "user", "quiz", "is_completed", "correct_count", "total_questions", "updated_at")
    list_select_related = ("user", "quiz")
    list_filter = ("is_completed", "updated_at")
    search_fields = ("user__username", "quiz__title")
    ordering = ("-updated_at",)
    readonly_fields = ("started_at", "completed_at", "updated_at")
    inlines = (AttemptAnswerInline,)


@admin.register(AttemptAnswer)
class AttemptAnswerAdmin(admin.ModelAdmin):
    """Admin-Ansicht für einzelne gespeicherte Antworten eines Attempts."""

    list_display = ("id", "attempt", "question", "selected_option", "is_correct", "created_at")
    list_select_related = ("attempt", "question")
    list_filter = ("is_correct", "created_at")
    search_fields = ("selected_option", "question__question_title")
    ordering = ("-created_at",)
