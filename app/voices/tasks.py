from __future__ import annotations

import requests

from celery import shared_task

from tts.resemble_client import (
    resemble_voice_design_generate,
    resemble_build_voice,
    resemble_create_custom_voice,
)


@shared_task(
    bind=True,
    autoretry_for=(requests.exceptions.RequestException,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
)
def voice_design_generate_task(self, user_prompt: str, is_voice_design_trial: bool = True) -> dict:
    return resemble_voice_design_generate(
        user_prompt=user_prompt,
        is_voice_design_trial=is_voice_design_trial,
    )


@shared_task(
    bind=True,
    autoretry_for=(requests.exceptions.RequestException,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
)
def voice_clone_create_task(self, payload: dict) -> dict:
    return resemble_create_custom_voice(payload)


@shared_task(
    bind=True,
    autoretry_for=(requests.exceptions.RequestException,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
)
def voice_clone_build_task(self, voice_uuid: str, fill: bool = False) -> dict:
    return resemble_build_voice(voice_uuid=voice_uuid, fill=fill)
