from __future__ import annotations

import logging
from typing import Any, Dict, List

from celery.result import AsyncResult

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import (
    VoicesListQuerySerializer,
    VoiceCreateSerializer,
    VoiceDesignGenerateSerializer,
    VoiceDesignCreateRapidFromCandidateSerializer,
    VoiceCloneDatasetUploadSerializer,
    VoiceCloneBuildSerializer,
    VoiceCloneCreateSerializer,
    VoiceCloneUploadRecordingSerializer
)
from .tasks import (
    voice_design_generate_task,
    voice_clone_build_task,
    voice_clone_create_task,
)

from tts.resemble_client import (
    resemble_list_voices,
    resemble_create_voice,
    resemble_voice_design_create_rapid_voice,
    resemble_get_voice,
    resemble_upload_voice_recording,
)

logger = logging.getLogger(__name__)


def _fetch_all_voices(advanced: bool) -> List[Dict[str, Any]]:
    """
    Resemble list voices is paginated.
    For 'My Voices' filtering, we fetch all pages (page_size=1000) then filter.
    """
    all_items: List[Dict[str, Any]] = []
    page = 1
    max_loops = 100  # safety guard

    while max_loops > 0:
        max_loops -= 1
        data = resemble_list_voices({"page": page, "page_size": 1000, "advanced": advanced}) or {}
        items = data.get("items") or []
        all_items.extend(items)

        num_pages = data.get("num_pages") or 1
        if page >= num_pages:
            break
        page += 1

    return all_items


class VoicesLibraryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        ser = VoicesListQuerySerializer(data=request.query_params)
        ser.is_valid(raise_exception=True)
        params = ser.validated_data

        data = resemble_list_voices(params)
        return Response(data, status=status.HTTP_200_OK)


class MyVoicesView(APIView):
    """
    My Voices page -> ONLY voices where item["source"] == "Custom Voice"
    We paginate AFTER filtering so UI pagination is correct.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        ser = VoicesListQuerySerializer(data=request.query_params)
        ser.is_valid(raise_exception=True)
        q = ser.validated_data

        page = q["page"]
        page_size = q["page_size"]
        advanced = q["advanced"]

        all_items = _fetch_all_voices(advanced=advanced)

        filtered = [v for v in all_items if (v.get("source") == "Custom Voice" or v.get("source") == "")]

        total_items = len(filtered)
        total_pages = max(1, (total_items + page_size - 1) // page_size)

        # Clamp page
        if page > total_pages:
            page = total_pages

        start = (page - 1) * page_size
        end = start + page_size
        page_items = filtered[start:end]

        # Return same list format as Resemble (page/num_pages/page_size/items)
        resp = {
            "success": True,
            "page": page,
            "num_pages": total_pages,
            "page_size": page_size,
            "items": page_items,
        }
        return Response(resp, status=status.HTTP_200_OK)


class CreateVoiceView(APIView):
    """
    Create a new voice -> proxies POST /api/v2/voices
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = VoiceCreateSerializer

    def post(self, request):
        ser = VoiceCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        payload = dict(ser.validated_data)
        payload = {k: v for k, v in payload.items() if v not in ("", None)}

        data = resemble_create_voice(payload)
        # docs show 200 on success for create voice
        return Response(data, status=status.HTTP_200_OK)


# Voice Design
class VoiceDesignGenerateCandidatesView(APIView):
    """
    POST JSON:
      { "user_prompt": "...", "is_voice_design_trial": true }
    Returns 202:
      { "success": true, "job_id": "<celery-task-id>" }
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = VoiceDesignGenerateSerializer

    def post(self, request):
        ser = VoiceDesignGenerateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        task = voice_design_generate_task.delay(
            ser.validated_data["user_prompt"],
            ser.validated_data.get("is_voice_design_trial", True),
        )
        return Response({"success": True, "job_id": task.id}, status=status.HTTP_202_ACCEPTED)


class VoiceDesignCreateRapidFromCandidateView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = VoiceDesignCreateRapidFromCandidateSerializer

    def post(self, request):
        ser = VoiceDesignCreateRapidFromCandidateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        v = ser.validated_data
        data = resemble_voice_design_create_rapid_voice(
            voice_design_model_uuid=v["voice_design_model_uuid"],
            voice_sample_index=v["voice_sample_index"],
            voice_name=v["voice_name"],
        )
        return Response({"success": True, **data}, status=status.HTTP_200_OK)


class VoiceDesignGenerateAsyncView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = VoiceDesignGenerateSerializer

    def post(self, request):
        ser = VoiceDesignGenerateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        task = voice_design_generate_task.delay(
            ser.validated_data["user_prompt"],
            ser.validated_data.get("is_voice_design_trial", True),
        )
        return Response({"success": True, "job_id": task.id}, status=status.HTTP_202_ACCEPTED)


class VoiceDesignJobStatusView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, job_id: str):
        res = AsyncResult(job_id)

        if res.successful():
            return Response({"success": True, "status": "completed", "result": res.result}, status=status.HTTP_200_OK)

        if res.failed():
            return Response({"success": False, "status": "failed", "error": str(res.result)}, status=status.HTTP_200_OK)

        return Response({"success": True, "status": res.status.lower()}, status=status.HTTP_200_OK)


# Voice Clone
class VoiceCloneDatasetUploadView(APIView):
    """
    POST multipart/form-data: { file: <wav|zip> }
    Saves into MEDIA and returns a public HTTPS url usable as dataset_url in Resemble.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = VoiceCloneDatasetUploadSerializer

    def post(self, request):
        ser = VoiceCloneDatasetUploadSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        f = ser.validated_data["file"]

        # store under media/voices_clone/YYYYMMDD/<uuid>_<orig>
        today = timezone.now().strftime("%Y%m%d")
        original_name = os.path.basename(getattr(f, "name", "dataset.bin"))
        safe_name = f"{uuid.uuid4().hex}_{original_name}"
        rel_path = f"voices_clone/{today}/{safe_name}"

        # save
        content = f.read()
        default_storage.save(rel_path, ContentFile(content))

        url = build_public_url(request, rel_path)
        return Response({"success": True, "dataset_url": url, "path": rel_path}, status=status.HTTP_200_OK)


class VoiceCloneCreateAsyncView(APIView):
    """
    POST JSON:
      { name, voice_type, language?, description?, dataset_url?, callback_uri? }
    Returns 202 with job_id. Result will contain Resemble response including voice uuid.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = VoiceCloneCreateSerializer

    def post(self, request):
        ser = VoiceCloneCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        payload = dict(ser.validated_data)
        payload = {k: v for k, v in payload.items() if v not in ("", None)}

        task = voice_clone_create_task.delay(payload)
        return Response({"success": True, "job_id": task.id}, status=status.HTTP_202_ACCEPTED)


class VoiceCloneUploadRecordingView(APIView):
    """
    POST multipart/form-data:
      voice_uuid, file, name, text?, emotion?, is_active?
    Forwards immediately to Resemble.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = VoiceCloneUploadRecordingSerializer

    def post(self, request):
        ser = VoiceCloneUploadRecordingSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        v = ser.validated_data

        f = v["file"]
        filename = os.path.basename(getattr(f, "name", "audio.wav"))
        content_type = getattr(f, "content_type", "") or ""

        data = resemble_upload_voice_recording(
            voice_uuid=v["voice_uuid"],
            file_obj=f,
            filename=filename,
            content_type=content_type,
            name=v["name"],
            text=v.get("text", "") or "",
            emotion=v.get("emotion", "neutral") or "neutral",
            is_active=bool(v.get("is_active", True)),
        )
        return Response({"success": True, **(data or {})}, status=status.HTTP_200_OK)


class VoiceCloneBuildAsyncView(APIView):
    """
    POST JSON:
      { voice_uuid, fill:false }
    Returns 202 with job_id.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = VoiceCloneBuildSerializer

    def post(self, request):
        ser = VoiceCloneBuildSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        v = ser.validated_data

        task = voice_clone_build_task.delay(v["voice_uuid"], v.get("fill", False))
        return Response({"success": True, "job_id": task.id}, status=status.HTTP_202_ACCEPTED)


class VoiceCloneGetVoiceView(APIView):
    """
    GET /clone/voices/<uuid>/
    Proxy voice status (pending/training/finished etc.).
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, voice_uuid: str):
        voice_uuid = (voice_uuid or "").strip()
        if not voice_uuid:
            return Response({"success": False, "error": "voice_uuid is required"}, status=status.HTTP_400_BAD_REQUEST)

        data = resemble_get_voice(voice_uuid)
        return Response({"success": True, **(data or {})}, status=status.HTTP_200_OK)


class VoiceCloneJobStatusView(APIView):
    """
    Reuse same job status pattern (AsyncResult).
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, job_id: str):
        res = AsyncResult(job_id)

        if res.successful():
            return Response({"success": True, "status": "completed", "result": res.result}, status=status.HTTP_200_OK)

        if res.failed():
            return Response({"success": False, "status": "failed", "error": str(res.result)}, status=status.HTTP_200_OK)

        return Response({"success": True, "status": res.status.lower()}, status=status.HTTP_200_OK)
