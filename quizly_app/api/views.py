from __future__ import annotations
from rest_framework import generics, permissions
from rest_framework.exceptions import PermissionDenied
from quizly_app.models import Quiz
from .serializers import QuizSerializer, QuizUpdateSerializer


class UserQuizQuerysetMixin:
    """Restrict queryset to the authenticated user's quizzes."""

    def get_queryset(self):
        return Quiz.objects.filter(user=self.request.user).prefetch_related("questions")


class QuizListView(UserQuizQuerysetMixin, generics.ListAPIView):
    """GET /api/quizzes/"""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = QuizSerializer


class QuizDetailView(UserQuizQuerysetMixin, generics.RetrieveUpdateDestroyAPIView):
    """GET/PATCH/DELETE /api/quizzes/{id}/"""

    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "pk"

    def get_serializer_class(self):
        if self.request.method == "PATCH":
            return QuizUpdateSerializer
        return QuizSerializer

    def perform_update(self, serializer):
      
        if serializer.instance.user_id != self.request.user.id:
            raise PermissionDenied("You do not have permission to modify this quiz.")
        serializer.save()

    def perform_destroy(self, instance):
        if instance.user_id != self.request.user.id:
            raise PermissionDenied("You do not have permission to delete this quiz.")
        instance.delete()
