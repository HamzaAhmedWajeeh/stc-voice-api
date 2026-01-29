from __future__ import annotations

from rest_framework import serializers


class VoicesListQuerySerializer(serializers.Serializer):
    page = serializers.IntegerField(required=False, default=1, min_value=1)
    page_size = serializers.IntegerField(required=False, default=10, min_value=10, max_value=1000)
    advanced = serializers.BooleanField(required=False, default=False)


class VoiceCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=80)
    voice_type = serializers.ChoiceField(
        choices=["rapid", "professional"],
        required=False,
        default="professional",
    )
    dataset_url = serializers.URLField(required=False, allow_blank=True)
    callback_uri = serializers.URLField(required=False, allow_blank=True)
    language = serializers.CharField(required=False, default="en-US")

    def validate_name(self, value: str) -> str:
        v = (value or "").strip()
        if not v:
            raise serializers.ValidationError("name is required.")
        return v


class VoiceDesignGenerateSerializer(serializers.Serializer):
    user_prompt = serializers.CharField(max_length=2000)
    is_voice_design_trial = serializers.BooleanField(required=False, default=True)

    def validate_user_prompt(self, value: str) -> str:
        v = (value or "").strip()
        if not v:
            raise serializers.ValidationError("user_prompt is required.")
        return v


class VoiceDesignCreateRapidFromCandidateSerializer(serializers.Serializer):
    # Accept BOTH: voice_design_model_uuid (new) OR uuid (older FE)
    voice_design_model_uuid = serializers.CharField(required=False, allow_blank=True)
    uuid = serializers.CharField(required=False, allow_blank=True)

    voice_sample_index = serializers.IntegerField(min_value=0, max_value=2)
    voice_name = serializers.CharField(max_length=80)

    def validate(self, attrs):
        vdm = (attrs.get("voice_design_model_uuid") or "").strip()
        legacy = (attrs.get("uuid") or "").strip()

        if not vdm and not legacy:
            raise serializers.ValidationError("voice_design_model_uuid (or uuid) is required.")

        attrs["voice_design_model_uuid"] = vdm or legacy

        name = (attrs.get("voice_name") or "").strip()
        if not name:
            raise serializers.ValidationError("voice_name is required.")
        attrs["voice_name"] = name

        return attrs


class VoiceDesignCreateFromCandidateSerializer(serializers.Serializer):
    uuid = serializers.CharField()
    voice_sample_index = serializers.IntegerField(min_value=0, max_value=2)
    name = serializers.CharField(max_length=80)

    def validate_uuid(self, value: str) -> str:
        v = (value or "").strip()
        if not v:
            raise serializers.ValidationError("uuid is required.")
        return v

    def validate_name(self, value: str) -> str:
        v = (value or "").strip()
        if not v:
            raise serializers.ValidationError("name is required.")
        return v


class VoiceCloneDatasetUploadSerializer(serializers.Serializer):
    file = serializers.FileField()

    def validate_file(self, f):
        # Keep demo-friendly defaults
        max_bytes = 200 * 1024 * 1024  # 200MB
        if f.size and f.size > max_bytes:
            raise serializers.ValidationError("Max upload size is 200MB for demo.")

        name = (getattr(f, "name", "") or "").lower()
        allowed = (".wav", ".zip", ".mp3", ".m4a", ".mp4", ".webm", ".mov")
        if allowed and not any(name.endswith(x) for x in allowed):
            raise serializers.ValidationError("Unsupported dataset file type.")
        return f


class VoiceCloneCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=256)
    voice_type = serializers.ChoiceField(choices=["rapid", "professional"], required=False, default="professional")
    language = serializers.CharField(required=False, default="en-US")
    description = serializers.CharField(required=False, allow_blank=True)
    dataset_url = serializers.URLField(required=False, allow_blank=True)
    callback_uri = serializers.URLField(required=False, allow_blank=True)

    def validate_name(self, value: str) -> str:
        v = (value or "").strip()
        if not v:
            raise serializers.ValidationError("name is required.")
        return v


class VoiceCloneUploadRecordingSerializer(serializers.Serializer):
    voice_uuid = serializers.CharField()
    file = serializers.FileField()
    name = serializers.CharField(max_length=128)
    text = serializers.CharField(required=False, allow_blank=True, default="")
    emotion = serializers.CharField(required=False, allow_blank=True, default="neutral")
    is_active = serializers.BooleanField(required=False, default=True)

    def validate_voice_uuid(self, value: str) -> str:
        v = (value or "").strip()
        if not v:
            raise serializers.ValidationError("voice_uuid is required.")
        return v

    def validate_name(self, value: str) -> str:
        v = (value or "").strip()
        if not v:
            raise serializers.ValidationError("name is required.")
        return v


class VoiceCloneBuildSerializer(serializers.Serializer):
    voice_uuid = serializers.CharField()
    fill = serializers.BooleanField(required=False, default=False)

    def validate_voice_uuid(self, value: str) -> str:
        v = (value or "").strip()
        if not v:
            raise serializers.ValidationError("voice_uuid is required.")
        return v
