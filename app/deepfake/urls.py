from django.urls import path
from . import views

urlpatterns = [
    path("meta/", views.DeepfakeMetaView.as_view(), name="deepfake-meta"),

    path("uploads/", views.DeepfakeUploadView.as_view(), name="deepfake-upload"),
    path("jobs/", views.DeepfakeJobsView.as_view(), name="deepfake-jobs"),
    path("jobs/<str:uuid>/", views.DeepfakeJobDetailView.as_view(), name="deepfake-job-detail"),

    path("detect/", views.DetectListCreateView.as_view(), name="deepfake-detect-list-create"),
    path("detect/<str:uuid>/", views.DetectDetailView.as_view(), name="deepfake-detect-detail"),
]
