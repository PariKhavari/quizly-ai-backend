from __future__ import annotations
from django.contrib import admin
from quizly_app.models import AttemptAnswer, Question, Quiz, QuizAttempt


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "user", "created_at", "updated_at")
    list_filter = ("created_at", "updated_at")
    search_fields = ("title", "description", "video_url", "user__username", "user__email")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-created_at",)
    

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("id", "quiz", "short_title", "created_at")
    list_filter = ("created_at",)
    search_fields = ("question_title", "answer", "quiz__title")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("id",)

    def short_title(self, obj: Question) -> str:
        return (obj.question_title[:60] + "...") if len(obj.question_title) > 60 else obj.question_title

    short_title.short_description = "Question"


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "quiz",
        "user",
        "is_completed",
        "current_question_index",
        "correct_count",
        "total_questions",
        "started_at",
        "completed_at",
    )
    list_filter = ("is_completed", "started_at", "completed_at")
    search_fields = ("quiz__title", "user__username", "user__email")
    readonly_fields = ("started_at", "completed_at", "updated_at")
    ordering = ("-started_at",)


@admin.register(AttemptAnswer)
class AttemptAnswerAdmin(admin.ModelAdmin):
    list_display = ("id", "attempt", "question", "selected_option", "is_correct", "updated_at")
    list_filter = ("is_correct", "updated_at")
    search_fields = ("selected_option", "question__question_title", "attempt__quiz__title")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-updated_at",)
