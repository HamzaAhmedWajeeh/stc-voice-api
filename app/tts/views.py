from __future__ import annotations

import logging
from typing import Dict, Any

from django.http import StreamingHttpResponse
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import (
    StreamSynthesizeSerializer,
    VoicesListQuerySerializer,
    VoiceSettingsPresetCreateSerializer,
    VoiceSettingsPresetUpdateSerializer,
    UUIDPathSerializer
)
from .resemble_client import (
    resemble_stream,
    resemble_list_voices,
    resemble_list_voice_settings_presets,
    resemble_create_voice_settings_preset,
    resemble_delete_voice_settings_preset,
    resemble_get_voice_settings_preset,
    resemble_update_voice_settings_preset
)

logger = logging.getLogger(__name__)


class TTSMetaView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        meta = {
            "models": [
                {"value": "", "label": "Auto (default by voice)"},
                {"value": "chatterbox-turbo", "label": "Chatterbox Turbo (low latency + tags)"},
                {"value": "tts-v4", "label": "Chatterbox (v4 code)"},
                {"value": "tts-v4-turbo", "label": "Chatterbox Turbo (v4 code)"},
                {"value": "tts-v3", "label": "Enhanced TTS v3 (deprecated)"},
            ],
            "output_formats": ["wav", "mp3"],
            "precisions": ["MULAW", "PCM_16", "PCM_24", "PCM_32"],
            "sample_rates": [8000, 16000, 22050, 32000, 44100, 48000],
            "notes": {
                "synthesize_model_param": "Use chatterbox-turbo for turbo mode when supported by the voice.",
                "voice_settings_presets": "Use voice_settings_preset_uuid to apply saved settings.",
            },
        }
        return Response(meta, status=status.HTTP_200_OK)


class StreamSynthesizeView(APIView):
    """
    Main endpoint for FE "Play" button.
    Returns streamed audio (WAV/MP3) that browser can play immediately.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = StreamSynthesizeSerializer

    def post(self, request):
        ser = StreamSynthesizeSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        payload = dict(ser.validated_data)
        payload = {k: v for k, v in payload.items() if v not in ("", None)}

        r = resemble_stream(payload)

        # Resemble returns chunked audio
        content_type = r.headers.get("Content-Type") or "audio/wav"

        def gen():
            try:
                for chunk in r.iter_content(chunk_size=64 * 1024):
                    if chunk:
                        yield chunk
            finally:
                r.close()

        resp = StreamingHttpResponse(gen(), content_type=content_type)

        # Stop proxies buffering the stream
        resp["Cache-Control"] = "no-cache"
        resp["X-Accel-Buffering"] = "no"

        # Help browser treat it as a playable file/stream
        resp["Content-Disposition"] = 'inline; filename="tts.wav"'

        return resp


class VoicesListProxyView(APIView):
    """
    Proxies Resemble voice listing (GET /api/v2/voices)

    Supports: page, page_size, advanced
    - GET: reads from query params
    - POST: reads from JSON body (kept for FE compatibility)
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = VoicesListQuerySerializer

    def _validated_params(self, request):
        raw = request.query_params if request.method == "GET" else request.data

        if request.method != "GET" and not raw:
            raw = request.query_params

        data = dict(raw)

        if "advanced" not in data:
            data["advanced"] = True

        if "page_size" not in data:
            data["page_size"] = 1000

        ser = VoicesListQuerySerializer(data=data)
        ser.is_valid(raise_exception=True)
        return ser.validated_data

    def get(self, request):
        params = self._validated_params(request)
        data = resemble_list_voices(params)
        return Response(data, status=status.HTTP_200_OK)

    def post(self, request):
        return self.get(request)
    

# ---------- Presets CRUD ----------

class VoiceSettingsPresetsListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = VoiceSettingsPresetCreateSerializer

    def get(self, request):
        data = resemble_list_voice_settings_presets()
        return Response(data, status=status.HTTP_200_OK)

    def post(self, request):
        ser = VoiceSettingsPresetCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        payload = {k: v for k, v in ser.validated_data.items() if v not in ("", None)}
        data = resemble_create_voice_settings_preset(payload)
        return Response(data, status=status.HTTP_201_CREATED)


class VoiceSettingsPresetDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UUIDPathSerializer

    def get(self, request, uuid: str):
        UUIDPathSerializer(data={"uuid": uuid}).is_valid(raise_exception=True)
        data = resemble_get_voice_settings_preset(uuid)
        return Response(data, status=status.HTTP_200_OK)

    def patch(self, request, uuid: str):
        UUIDPathSerializer(data={"uuid": uuid}).is_valid(raise_exception=True)
        ser = VoiceSettingsPresetUpdateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        payload = {k: v for k, v in ser.validated_data.items() if v not in ("", None)}
        data = resemble_update_voice_settings_preset(uuid, payload)
        return Response(data, status=status.HTTP_200_OK)

    def delete(self, request, uuid: str):
        UUIDPathSerializer(data={"uuid": uuid}).is_valid(raise_exception=True)
        data = resemble_delete_voice_settings_preset(uuid)
        return Response(data, status=status.HTTP_200_OK)
