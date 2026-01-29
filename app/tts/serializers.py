from __future__ import annotations
from rest_framework import serializers


class StreamSynthesizeSerializer(serializers.Serializer):
    voice_uuid = serializers.CharField()
    data = serializers.CharField(max_length=2000)  # per docs for stream

    # Optional
    model = serializers.CharField(required=False, allow_blank=True)

    precision = serializers.ChoiceField(
        choices=["MULAW", "PCM_16", "PCM_24", "PCM_32"],
        required=False,
    )
    output_format = serializers.ChoiceField(choices=["wav", "mp3"], required=False)
    sample_rate = serializers.IntegerField(required=False)
    use_hd = serializers.BooleanField(required=False)

    voice_settings_preset_uuid = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        # normalize empty strings to ""
        for k, v in list(attrs.items()):
            if isinstance(v, str):
                attrs[k] = v.strip()

        if not attrs.get("voice_uuid"):
            raise serializers.ValidationError({"voice_uuid": "voice_uuid is required."})

        if not attrs.get("data"):
            raise serializers.ValidationError({"data": "Text is required."})

        return attrs


class VoicesListQuerySerializer(serializers.Serializer):
    page = serializers.IntegerField(required=False, default=1, min_value=1)
    page_size = serializers.IntegerField(required=False, default=10, min_value=10, max_value=1000)
    advanced = serializers.BooleanField(required=False, default=False)


class VoiceSettingsPresetCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=30)

    pace = serializers.FloatField(required=False, min_value=0.2, max_value=2.0)
    temperature = serializers.FloatField(required=False, min_value=0.1, max_value=5.0)
    pitch = serializers.FloatField(required=False, min_value=-10.0, max_value=10.0)
    useHd = serializers.BooleanField(required=False)
    exaggeration = serializers.FloatField(required=False, min_value=0.0, max_value=1.0)
    description = serializers.CharField(required=False, max_length=1000, allow_blank=True)

    def validate_name(self, value: str) -> str:
        v = (value or "").strip()
        if not v:
            raise serializers.ValidationError("Preset name is required.")
        return v


class VoiceSettingsPresetUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(required=False, max_length=30)

    pace = serializers.FloatField(required=False, min_value=0.2, max_value=2.0)
    temperature = serializers.FloatField(required=False, min_value=0.1, max_value=5.0)
    pitch = serializers.FloatField(required=False, min_value=-10.0, max_value=10.0)
    useHd = serializers.BooleanField(required=False)
    exaggeration = serializers.FloatField(required=False, min_value=0.0, max_value=1.0)
    description = serializers.CharField(required=False, max_length=1000, allow_blank=True)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("At least one field is required for update.")
        if "name" in attrs:
            attrs["name"] = (attrs["name"] or "").strip()
            if not attrs["name"]:
                raise serializers.ValidationError({"name": "Name cannot be empty."})
        return attrs


class UUIDPathSerializer(serializers.Serializer):
    uuid = serializers.CharField()

    def validate_uuid(self, value: str) -> str:
        v = (value or "").strip()
        if not v:
            raise serializers.ValidationError("uuid is required.")
        return v
