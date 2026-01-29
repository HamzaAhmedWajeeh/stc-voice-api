from __future__ import annotations

import os
import hashlib

from django.conf import settings


from rest_framework import serializers

from core.models import (
    DeepfakeUpload,
    DeepfakeDetectJob,
)


class DetectListQuerySerializer(serializers.Serializer):
    page = serializers.IntegerField(required=False, default=1, min_value=1)
    page_size = serializers.IntegerField(required=False, default=10, min_value=10, max_value=1000)


class DetectCreateSerializer(serializers.Serializer):
    # required
    url = serializers.URLField()

    # optional
    callback_url = serializers.URLField(required=False, allow_blank=True)
    visualize = serializers.BooleanField(required=False)
    frame_length = serializers.IntegerField(required=False, min_value=1, max_value=4)

    start_region = serializers.FloatField(required=False)
    end_region = serializers.FloatField(required=False)

    pipeline = serializers.CharField(required=False, allow_blank=True)
    max_video_fps = serializers.FloatField(required=False)
    max_video_secs = serializers.FloatField(required=False)

    model_types = serializers.ChoiceField(
        choices=["image", "talking_head"],
        required=False,
    )

    intelligence = serializers.BooleanField(required=False, default=False)
    audio_source_tracing_enabled = serializers.BooleanField(required=False, default=False)
    use_ood_detector = serializers.BooleanField(required=False, default=False)

    extra_params = serializers.DictField(required=False)

    def validate_url(self, value: str) -> str:
        v = (value or "").strip()
        if not v:
            raise serializers.ValidationError("url is required.")
        if not v.startswith("https://"):
            raise serializers.ValidationError("url must be HTTPS (https://...) per Resemble docs.")
        return v

    def validate(self, attrs):
        # allow -1 behavior? docs show optional. UI uses -1 as “from start” & “to end”.
        # If FE sends -1, we remove it so Resemble doesn't get weird values.
        for k in ("start_region", "end_region"):
            if k in attrs and attrs[k] is not None and attrs[k] < 0:
                attrs.pop(k, None)

        # remove blanks
        for k in ["callback_url", "pipeline"]:
            if k in attrs and (attrs[k] == "" or attrs[k] is None):
                attrs.pop(k, None)

        return attrs


class UUIDPathSerializer(serializers.Serializer):
    uuid = serializers.CharField()

    def validate_uuid(self, value: str) -> str:
        v = (value or "").strip()
        if not v:
            raise serializers.ValidationError("uuid is required.")
        return v


def _safe_ext(filename: str) -> str:
    base = (filename or "").split("/")[-1].split("\\")[-1]
    ext = base.rsplit(".", 1)[-1].lower() if "." in base else ""
    return ext


class DeepfakeUploadSerializer(serializers.Serializer):
    file = serializers.FileField()

    def validate_file(self, f):
        if f.size and f.size > settings.DEEFAKE_UPLOAD_MAX_BYTES:
            raise serializers.ValidationError(f"Max file size is {settings.DEEFAKE_UPLOAD_MAX_BYTES} bytes.")

        ext = _safe_ext(getattr(f, "name", ""))
        if settings.DEEFAKE_ALLOWED_EXTS and ext not in settings.DEEFAKE_ALLOWED_EXTS:
            raise serializers.ValidationError(f"Unsupported file extension: .{ext}")

        ct = getattr(f, "content_type", "") or ""
        if settings.DEEFAKE_ALLOWED_MIME_PREFIXES and not any(ct.startswith(p) for p in settings.DEEFAKE_ALLOWED_MIME_PREFIXES):
            # Some clients may not send content_type properly; treat as soft check if empty
            if ct:
                raise serializers.ValidationError(f"Unsupported content type: {ct}")

        return f


class DeepfakeUploadResponseSerializer(serializers.ModelSerializer):

    class Meta:
        model = DeepfakeUpload
        fields = ["uuid", "original_name", "content_type", "size_bytes", "sha256", "created_at", "file"]


class DetectCreateFromUploadSerializer(serializers.Serializer):
    upload_uuid = serializers.UUIDField()

    # Mirror Resemble detect params (subset)
    callback_url = serializers.URLField(required=False, allow_blank=True)
    visualize = serializers.BooleanField(required=False, default=True)
    frame_length = serializers.IntegerField(required=False, min_value=1, max_value=4, default=2)

    start_region = serializers.FloatField(required=False)
    end_region = serializers.FloatField(required=False)

    pipeline = serializers.CharField(required=False, allow_blank=True)
    max_video_fps = serializers.FloatField(required=False)
    max_video_secs = serializers.FloatField(required=False)
    model_types = serializers.ChoiceField(choices=["image", "talking_head"], required=False)

    intelligence = serializers.BooleanField(required=False, default=False)
    audio_source_tracing_enabled = serializers.BooleanField(required=False, default=False)
    use_ood_detector = serializers.BooleanField(required=False, default=False)

    def validate(self, attrs):
        # UI sends -1 to mean "unset"
        for k in ("start_region", "end_region"):
            if k in attrs and attrs[k] == -1:
                attrs.pop(k, None)
        return attrs


class DeepfakeDetectJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeepfakeDetectJob
        fields = [
            "uuid",
            "status",
            "celery_task_id",
            "remote_detect_uuid",
            "request_payload",
            "create_response",
            "error_message",
            "created_at",
            "updated_at",
        ]
