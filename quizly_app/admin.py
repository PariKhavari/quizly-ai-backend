from __future__ import annotations
from django.contrib import admin
from .models import Quiz, Question


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 0
    fields = ("question_title", "question_options", "answer", "created_at", "updated_at")
    readonly_fields = ("created_at", "updated_at")
    show_change_link = True


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "user", "created_at", "updated_at")
    list_filter = ("created_at", "updated_at")
    search_fields = ("title", "description", "video_url", "user__username", "user__email")
    readonly_fields = ("created_at", "updated_at")
    fields = ("user", "title", "description", "video_url", "created_at", "updated_at")
    inlines = [QuestionInline]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("id", "quiz", "created_at", "updated_at")
    list_filter = ("created_at", "updated_at")
    search_fields = ("question_title", "answer", "quiz__title")
    readonly_fields = ("created_at", "updated_at")
    fields = ("quiz", "question_title", "question_options", "answer", "created_at", "updated_at")
