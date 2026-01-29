from django.urls import path
from . import views

urlpatterns = [
    path("transcripts/", views.TranscriptsListCreateView.as_view(), name="stt-transcripts"),
    path("transcripts/<str:uuid>/", views.TranscriptDetailView.as_view(), name="stt-transcript-detail"),
    path("transcripts/<str:uuid>/ask/", views.TranscriptAskView.as_view(), name="stt-transcript-ask"),
    path("transcripts/<str:uuid>/questions/", views.TranscriptQuestionsListView.as_view(), name="stt-transcript-questions"),
    path(
        "transcripts/<str:uuid>/questions/<str:question_uuid>/",
        views.TranscriptQuestionDetailView.as_view(),
        name="stt-transcript-question-detail",
    ),
]
