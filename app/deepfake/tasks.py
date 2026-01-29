from __future__ import annotations

import logging
from celery import shared_task
from django.db import transaction

from core.models import DeepfakeDetectJob
from tts.resemble_client import resemble_detect_create

logger = logging.getLogger(__name__)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_jitter=True, max_retries=3)
def create_detect_job_task(self, job_uuid: str) -> dict:
    """
    Creates a Resemble detect object using the uploaded file URL.
    Stores remote detect uuid and response.
    """
    job = DeepfakeDetectJob.objects.select_related("upload").get(uuid=job_uuid)

    with transaction.atomic():
        job.status = DeepfakeDetectJob.Status.RUNNING
        job.celery_task_id = self.request.id or ""
        job.save(update_fields=["status", "celery_task_id", "updated_at"])

    payload = dict(job.request_payload or {})
    try:
        resp = resemble_detect_create(payload) or {}
        item = resp.get("item") or {}
        remote_uuid = item.get("uuid") or ""

        with transaction.atomic():
            job.status = DeepfakeDetectJob.Status.SUCCEEDED
            job.remote_detect_uuid = remote_uuid
            job.create_response = resp
            job.error_message = ""
            job.save(update_fields=["status", "remote_detect_uuid", "create_response", "error_message", "updated_at"])
        return {"success": True, "remote_detect_uuid": remote_uuid, "response": resp}

    except Exception as e:
        logger.exception("Detect create failed for job=%s", job_uuid)
        with transaction.atomic():
            job.status = DeepfakeDetectJob.Status.FAILED
            job.error_message = str(e)
            job.save(update_fields=["status", "error_message", "updated_at"])
        raise
