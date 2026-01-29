from django.urls import path
from . import views

urlpatterns = [
    path("meta/", views.TTSMetaView.as_view(), name="tts-meta"),
    path("voices/", views.VoicesListProxyView.as_view(), name="tts-voices"),

    path("voice-settings-presets/", views.VoiceSettingsPresetsListCreateView.as_view(), name="tts-presets-list-create"),
    path("voice-settings-presets/<str:uuid>/", views.VoiceSettingsPresetDetailView.as_view(), name="tts-presets-detail"),

    path("stream/", views.StreamSynthesizeView.as_view(), name="tts-stream"),
]
