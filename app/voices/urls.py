from django.urls import path
from . import views

urlpatterns = [
    path("library/", views.VoicesLibraryView.as_view(), name="voices-library"),
    path("my/", views.MyVoicesView.as_view(), name="voices-my"),
    path("create/", views.CreateVoiceView.as_view(), name="voices-create"),

     # Voice Design
    path("design/generate/", views.VoiceDesignGenerateCandidatesView.as_view()),
    path("design/jobs/<str:job_id>/", views.VoiceDesignJobStatusView.as_view()),
    path("design/create-rapid/", views.VoiceDesignCreateRapidFromCandidateView.as_view()),

    # Voice Clone
    path("clone/dataset/upload/", views.VoiceCloneDatasetUploadView.as_view()),
    path("clone/create-async/", views.VoiceCloneCreateAsyncView.as_view()),
    path("clone/jobs/<str:job_id>/", views.VoiceCloneJobStatusView.as_view()),
    path("clone/recordings/upload/", views.VoiceCloneUploadRecordingView.as_view()),
    path("clone/build-async/", views.VoiceCloneBuildAsyncView.as_view()),
    path("clone/voices/<str:voice_uuid>/", views.VoiceCloneGetVoiceView.as_view()),
]
