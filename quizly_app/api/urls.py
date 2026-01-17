from django.urls import path
from .views import QuizListView, QuizDetailView, CreateQuizView

urlpatterns = [
    path("createQuiz/", CreateQuizView.as_view(), name="quiz-create"),
    path("quizzes/", QuizListView.as_view(), name="quiz-list"),
    path("quizzes/<int:pk>/", QuizDetailView.as_view(), name="quiz-detail"),
]