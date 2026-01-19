from django.urls import path
from .views import AttemptDetailView, AttemptResultView, FinishAttemptView, QuizListView, QuizDetailView, CreateQuizView, SaveAnswerView, StartAttemptView

urlpatterns = [
    path("createQuiz/", CreateQuizView.as_view(), name="quiz-create"),
    path("quizzes/", QuizListView.as_view(), name="quiz-list"),
    path("quizzes/<int:quiz_id>/", QuizDetailView.as_view(), name="quiz-detail"),
    path("quizzes/<int:quiz_id>/start/", StartAttemptView.as_view(), name="attempt-start"),
    path("attempts/<int:attempt_id>/", AttemptDetailView.as_view(), name="attempt-detail"),
    path("attempts/<int:attempt_id>/answer/", SaveAnswerView.as_view(), name="attempt-answer"),
    path("attempts/<int:attempt_id>/finish/", FinishAttemptView.as_view(), name="attempt-finish"),
    path("attempts/<int:attempt_id>/result/", AttemptResultView.as_view(), name="attempt-result"),
]