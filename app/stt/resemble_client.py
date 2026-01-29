from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from tts.resemble_client import (
    RESEMBLE_APP_API_BASE,
    get_json,
    post_json,
    post_multipart,
)

# ---- Speech-to-Text endpoints ----

def resemble_list_transcripts(params: Dict[str, Any]) -> Dict[str, Any]:
    allowed = {"page", "per_page"}
    clean = {k: v for k, v in (params or {}).items() if k in allowed and v is not None}
    # page is required per docs; serializers will always provide it
    return get_json(f"{RESEMBLE_APP_API_BASE}/api/v2/speech-to-text", params=clean, timeout=60)


def resemble_create_transcript_job(
    *,
    file_tuple: Optional[Tuple[str, Any, str]] = None,
    query: Optional[str] = None,
) -> Dict[str, Any]:
    data: Dict[str, Any] = {}
    if query:
        data["query"] = query

    files = None
    if file_tuple:
        files = {"file": file_tuple}

    return post_multipart(
        f"{RESEMBLE_APP_API_BASE}/api/v2/speech-to-text",
        data=data,
        files=files,
        timeout=120,
    )


def resemble_get_transcript(uuid: str) -> Dict[str, Any]:
    return get_json(f"{RESEMBLE_APP_API_BASE}/api/v2/speech-to-text/{uuid}", timeout=60)


def resemble_ask_transcript(uuid: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    return post_json(f"{RESEMBLE_APP_API_BASE}/api/v2/speech-to-text/{uuid}/ask", payload, timeout=60)


def resemble_list_questions(uuid: str, params: Dict[str, Any]) -> Dict[str, Any]:
    allowed = {"page", "per_page"}
    clean = {k: v for k, v in (params or {}).items() if k in allowed and v is not None}
    return get_json(f"{RESEMBLE_APP_API_BASE}/api/v2/speech-to-text/{uuid}/questions", params=clean, timeout=60)


def resemble_get_question(uuid: str, question_uuid: str) -> Dict[str, Any]:
    return get_json(
        f"{RESEMBLE_APP_API_BASE}/api/v2/speech-to-text/{uuid}/questions/{question_uuid}",
        timeout=60,
    )
