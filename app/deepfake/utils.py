from __future__ import annotations

from django.conf import settings

from urllib.parse import urljoin


def build_public_url(request, relative_path_under_media: str) -> str:
    """
    relative_path_under_media: DeepfakeUpload.file.name
    example: "deepfake/20260128/abc.wav"
    """
    base = getattr(settings, "PUBLIC_BASE_URL", None) or request.build_absolute_uri("/").rstrip("/")
    # MEDIA_URL is "/static/media/"
    return urljoin(base.rstrip("/") + "/", (settings.MEDIA_URL.lstrip("/") + relative_path_under_media))
