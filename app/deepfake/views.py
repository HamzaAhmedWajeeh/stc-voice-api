from __future__ import annotations

import hashlib
import os
from django.core.files.storage import default_storage
from django.db import transaction
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import DeepfakeUpload, DeepfakeDetectJob
from .serializers import (
    DeepfakeUploadSerializer,
    DeepfakeUploadResponseSerializer,
    DetectCreateFromUploadSerializer,
    DeepfakeDetectJobSerializer,
    DetectListQuerySerializer,
    DetectCreateSerializer,
    UUIDPathSerializer,
)
from .utils import build_public_url
from .tasks import create_detect_job_task

from tts.resemble_client import resemble_detect_list, resemble_detect_create, resemble_detect_get


class DeepfakeUploadView(APIView):
    """
    POST multipart/form-data: { file: <local file> }
    Returns: upload_uuid + public url.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DeepfakeUploadSerializer

    def post(self, request):
        ser = DeepfakeUploadSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        f = ser.validated_data["file"]

        # compute sha256 while streaming
        sha = hashlib.sha256()
        for chunk in f.chunks():
            sha.update(chunk)
        digest = sha.hexdigest()

        # Rewind file pointer for saving (important after reading chunks)
        try:
            f.seek(0)
        except Exception:
            pass

        original_name = os.path.basename(getattr(f, "name", "upload.bin"))
        content_type = getattr(f, "content_type", "") or ""
        size_bytes = getattr(f, "size", 0) or 0

        # Save using FileField so path is managed by Django
        upload = DeepfakeUpload(
            user=request.user,
            original_name=original_name,
            content_type=content_type,
            size_bytes=size_bytes,
            sha256=digest,
        )
        upload.file.save(original_name, f, save=True)

        url = build_public_url(request, upload.file.name)

        data = DeepfakeUploadResponseSerializer(upload).data
        data["url"] = url
        return Response({"success": True, "item": data}, status=status.HTTP_200_OK)


class DeepfakeJobsView(APIView):
    """
    POST: create async detect job from an upload_uuid + settings.
    GET: (optional) list jobs per user (simple).
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DetectCreateFromUploadSerializer

    def post(self, request):
        ser = DetectCreateFromUploadSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        v = ser.validated_data

        upload = DeepfakeUpload.objects.filter(uuid=v["upload_uuid"], user=request.user).first()
        if not upload:
            return Response({"detail": "Upload not found."}, status=status.HTTP_404_NOT_FOUND)

        # Build Resemble payload (must include URL)
        url = build_public_url(request, upload.file.name)

        payload = dict(v)
        payload.pop("upload_uuid", None)
        payload["url"] = url

        # strip blanks
        payload = {k: val for k, val in payload.items() if val not in ("", None)}

        with transaction.atomic():
            job = DeepfakeDetectJob.objects.create(
                user=request.user,
                upload=upload,
                status=DeepfakeDetectJob.Status.QUEUED,
                request_payload=payload,
            )

        # enqueue celery
        task = create_detect_job_task.delay(str(job.uuid))
        DeepfakeDetectJob.objects.filter(uuid=job.uuid).update(celery_task_id=task.id or "")

        return Response(
            {
                "success": True,
                "job_uuid": str(job.uuid),
                "status": job.status,
                "celery_task_id": task.id,
                "notes": "Poll /api/deepfake/jobs/<job_uuid>/ until status=succeeded; then use remote_detect_uuid with /api/deepfake/detect/<uuid>/",
            },
            status=status.HTTP_202_ACCEPTED,
        )

    def get(self, request):
        qs = DeepfakeDetectJob.objects.filter(user=request.user).order_by("-created_at")[:50]
        return Response({"success": True, "items": DeepfakeDetectJobSerializer(qs, many=True).data}, status=status.HTTP_200_OK)


class DeepfakeJobDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, uuid: str):
        job = DeepfakeDetectJob.objects.filter(uuid=uuid, user=request.user).first()
        if not job:
            return Response({"detail": "Job not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response({"success": True, "item": DeepfakeDetectJobSerializer(job).data}, status=status.HTTP_200_OK)


class DeepfakeMetaView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(
            {
                "frame_length_choices": [1, 2, 3, 4],
                "model_types": ["image", "talking_head"],
                "defaults": {
                    "visualize": True,
                    "frame_length": 2,
                    "intelligence": False,
                    "audio_source_tracing_enabled": False,
                    "use_ood_detector": False,
                },
                "notes": {
                    "url": "Must be HTTPS URL accessible by Resemble servers.",
                    "start_region/end_region": "Send nothing (or -1 in UI -> backend strips) to mean full file.",
                },
            },
            status=status.HTTP_200_OK,
        )


class DetectListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DetectCreateSerializer

    def get(self, request):
        ser = DetectListQuerySerializer(data=request.query_params)
        ser.is_valid(raise_exception=True)
        data = resemble_detect_list(ser.validated_data)
        return Response(data, status=status.HTTP_200_OK)

    def post(self, request):
        # keep direct URL create if you still want it
        ser = DetectCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        payload = {k: v for k, v in ser.validated_data.items() if v not in ("", None)}
        data = resemble_detect_create(payload)
        return Response(data, status=status.HTTP_200_OK)


class DetectDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, uuid: str):
        UUIDPathSerializer(data={"uuid": uuid}).is_valid(raise_exception=True)
        data = resemble_detect_get(uuid)
        return Response(data, status=status.HTTP_200_OK)
