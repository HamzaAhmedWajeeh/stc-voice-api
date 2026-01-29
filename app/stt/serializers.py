from __future__ import annotations

from rest_framework import serializers

MAX_FILE_SIZE_BYTES = 500 * 1024 * 1024  # 500MB


class TranscriptListQuerySerializer(serializers.Serializer):
    page = serializers.IntegerField(required=False, default=1, min_value=1)
    per_page = serializers.IntegerField(required=False, default=25, min_value=1, max_value=50)


class TranscriptCreateSerializer(serializers.Serializer):
    file = serializers.FileField(required=False)
    query = serializers.CharField(required=False, allow_blank=True)

    def validate_file(self, f):
        if f.size > MAX_FILE_SIZE_BYTES:
            raise serializers.ValidationError("Max file size is 500MB.")
        return f

    def validate(self, attrs):
        # file is optional per docs, but UI expects it. We'll allow both.
        q = (attrs.get("query") or "").strip()
        if "query" in attrs:
            attrs["query"] = q
        return attrs


class UUIDPathSerializer(serializers.Serializer):
    uuid = serializers.UUIDField()


class AskQuestionSerializer(serializers.Serializer):
    query = serializers.CharField()

    def validate_query(self, value: str) -> str:
        v = (value or "").strip()
        if not v:
            raise serializers.ValidationError("query is required.")
        return v


class QuestionsListQuerySerializer(serializers.Serializer):
    page = serializers.IntegerField(required=False, default=1, min_value=1)
    per_page = serializers.IntegerField(required=False, default=25, min_value=1, max_value=50)


class QuestionUUIDPathSerializer(serializers.Serializer):
    question_uuid = serializers.UUIDField()
