from __future__ import annotations
from rest_framework import generics, permissions
from rest_framework.exceptions import PermissionDenied
from quizly_app.models import Quiz
from .serializers import QuizSerializer, QuizUpdateSerializer, CreateQuizSerializer
from rest_framework import status
from rest_framework.response import Response
from quizly_app.services.quiz_creation import create_quiz_for_user
from quizly_app.services.utils import QuizlyValidationError


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


class CreateQuizView(generics.GenericAPIView):
    """POST /api/createQuiz/"""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CreateQuizSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            quiz = create_quiz_for_user(user=request.user, url=serializer.validated_data["url"])
        except QuizlyValidationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            return Response({"detail": "Internal server error."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(QuizSerializer(quiz).data, status=status.HTTP_201_CREATED)
