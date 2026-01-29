from __future__ import annotations

import os
import requests
from typing import Any, Dict, Optional, Iterable, Tuple

RESEMBLE_SYNTH_BASE = os.environ.get("RESEMBLE_SYNTH_BASE", "https://f.cluster.resemble.ai")
RESEMBLE_APP_API_BASE = os.environ.get("RESEMBLE_APP_API_BASE", "https://app.resemble.ai")

def _bearer_headers(*, json: bool = True) -> Dict[str, str]:
    api_key = os.environ.get("RESEMBLE_API_KEY")
    if not api_key:
        raise RuntimeError("RESEMBLE_API_KEY is not set")

    headers = {"Authorization": f"Bearer {api_key}"}
    if json:
        headers["Content-Type"] = "application/json"
    return headers

def _auth_headers() -> Dict[str, str]:
    api_key = os.environ.get("RESEMBLE_API_KEY")
    if not api_key:
        raise RuntimeError("RESEMBLE_API_KEY is not set")
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

def _parse_json_or_raise(r: requests.Response) -> Dict[str, Any]:
    try:
        data = r.json()
    except Exception:
        r.raise_for_status()
        raise
    if r.status_code >= 400:
        raise requests.HTTPError(f"Resemble error {r.status_code}: {data}", response=r)
    return data

def post_json(url: str, payload: Dict[str, Any], *, timeout: int = 60) -> Dict[str, Any]:
    r = requests.post(url, json=payload, headers=_auth_headers(), timeout=timeout)
    # If Resemble returns non-200 with JSON, keep it readable
    try:
        data = r.json()
    except Exception:
        r.raise_for_status()
        raise
    if r.status_code >= 400:
        # bubble up as readable error
        raise requests.HTTPError(f"Resemble error {r.status_code}: {data}", response=r)
    return data

def get_json(url: str, *, params: Optional[Dict[str, Any]] = None, timeout: int = 30) -> Dict[str, Any]:
    r = requests.get(url, params=params or {}, headers=_auth_headers(), timeout=timeout)
    try:
        data = r.json()
    except Exception:
        r.raise_for_status()
        raise
    if r.status_code >= 400:
        raise requests.HTTPError(f"Resemble error {r.status_code}: {data}", response=r)
    return data

def post_stream(url: str, payload: Dict[str, Any], *, timeout: int = 60) -> requests.Response:
    # caller will iterate over bytes
    r = requests.post(url, json=payload, headers=_auth_headers(), timeout=timeout, stream=True)
    if r.status_code >= 400:
        # try to read JSON error body
        try:
            err = r.json()
        except Exception:
            r.raise_for_status()
        raise requests.HTTPError(f"Resemble error {r.status_code}: {err}", response=r)
    return r

def post_multipart(
    url: str,
    *,
    data: Optional[Dict[str, Any]] = None,
    files: Optional[Dict[str, Tuple[str, Any, str]]] = None,
    timeout: int = 120,
) -> Dict[str, Any]:
    """
    files format:
      {"file": (filename, fileobj, content_type)}
    """
    r = requests.post(
        url,
        data=data or {},
        files=files or None,
        headers=_bearer_headers(json=False),  # IMPORTANT: don't force JSON for multipart
        timeout=timeout,
    )
    return _parse_json_or_raise(r)

def patch_json(url: str, payload: Dict[str, Any], *, timeout: int = 60) -> Dict[str, Any]:
    r = requests.patch(url, json=payload, headers=_auth_headers(), timeout=timeout)
    return _parse_json_or_raise(r)

def delete_json(url: str, *, timeout: int = 60) -> Dict[str, Any]:
    r = requests.delete(url, headers=_auth_headers(), timeout=timeout)
    return _parse_json_or_raise(r)

def resemble_stream(payload: Dict[str, Any]) -> requests.Response:
    return post_stream(f"{RESEMBLE_SYNTH_BASE}/stream", payload, timeout=120)


# -------- Voices --------
def resemble_list_voices(params: Dict[str, Any]) -> Dict[str, Any]:
    allowed = {"page", "page_size", "advanced"}
    clean = {k: v for k, v in (params or {}).items() if k in allowed and v is not None}
    return get_json(f"{RESEMBLE_APP_API_BASE}/api/v2/voices", params=clean, timeout=60)


# -------- Presets CRUD --------
def resemble_list_voice_settings_presets() -> Dict[str, Any]:
    return get_json(f"{RESEMBLE_APP_API_BASE}/api/v2/voice_settings_presets", timeout=60)

def resemble_create_voice_settings_preset(payload: Dict[str, Any]) -> Dict[str, Any]:
    return post_json(f"{RESEMBLE_APP_API_BASE}/api/v2/voice_settings_presets", payload, timeout=60)

def resemble_get_voice_settings_preset(uuid: str) -> Dict[str, Any]:
    return get_json(f"{RESEMBLE_APP_API_BASE}/api/v2/voice_settings_presets/{uuid}", timeout=60)

def resemble_update_voice_settings_preset(uuid: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    return patch_json(f"{RESEMBLE_APP_API_BASE}/api/v2/voice_settings_presets/{uuid}", payload, timeout=60)

def resemble_delete_voice_settings_preset(uuid: str) -> Dict[str, Any]:
    return delete_json(f"{RESEMBLE_APP_API_BASE}/api/v2/voice_settings_presets/{uuid}", timeout=60)


# VOICES CRUD
def resemble_create_voice(payload: Dict[str, Any]) -> Dict[str, Any]:
    return post_json(f"{RESEMBLE_APP_API_BASE}/api/v2/voices", payload, timeout=60)


# -------- Voice Design --------
def resemble_voice_design_generate(
    *,
    user_prompt: str,
    is_voice_design_trial: Optional[bool] = True,
    timeout: int = 120,
) -> Dict[str, Any]:
    """
    Robust generate:
      - Try JSON body first (some newer docs show JSON payload)
      - Fallback to multipart (official API reference shows multipart form) :contentReference[oaicite:1]{index=1}
    Normalizes result to a stable internal shape:
      {
        "voice_candidates": {
          "voice_design_model_uuid": "<uuid>",
          "samples": [{"audio_url": "...", "sample_index": 0}, ...]
        }
      }
    """
    url = f"{RESEMBLE_APP_API_BASE}/api/v2/voice-design"

    # 1) Try JSON (newer style some docs mention)
    json_payload = {"user_prompt": user_prompt}
    if is_voice_design_trial is not None:
        json_payload["is_voice_design_trial"] = bool(is_voice_design_trial)

    try:
        r = requests.post(url, json=json_payload, headers=_auth_headers(), timeout=timeout)
        data = _parse_json_or_raise(r)
        return _normalize_voice_design_generate_response(data)
    except requests.HTTPError as e:
        # Fallback only for "unsupported media type" / "bad request-ish"
        resp = getattr(e, "response", None)
        status_code = getattr(resp, "status_code", None)
        if status_code not in (400, 404, 415, 422):
            raise

    # 2) Fallback: multipart (per API reference / guide) :contentReference[oaicite:2]{index=2}
    data = post_multipart(
        url,
        data={"user_prompt": user_prompt},
        timeout=timeout,
    )
    return _normalize_voice_design_generate_response(data)

def resemble_voice_design_create_rapid_voice(
    *,
    voice_design_model_uuid: str,
    voice_sample_index: int,
    voice_name: str,
    timeout: int = 60,
) -> Dict[str, Any]:
    """
    POST https://app.resemble.ai/api/v2/voice-design/{voice_design_model_uuid}/{voice_sample_index}/create_rapid_voice
    Docs show JSON body with voice_name, returns 202 Accepted. :contentReference[oaicite:3]{index=3}
    """
    url = (
        f"{RESEMBLE_APP_API_BASE}/api/v2/voice-design/"
        f"{voice_design_model_uuid}/{voice_sample_index}/create_rapid_voice"
    )
    payload = {"voice_name": voice_name}
    # keep JSON content-type
    r = requests.post(url, json=payload, headers=_auth_headers(), timeout=timeout)
    return _parse_json_or_raise(r)

def _normalize_voice_design_generate_response(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Resemble may return either:
      A) {"voice_candidates": [{"audio_url":..., "voice_sample_index":0, "uuid":"abcd"} ...]} :contentReference[oaicite:4]{index=4}
      B) {"voice_candidates": {"voice_design_model_uuid": "...", "samples": [{"audio_url":..., "sample_index":0}, ...]}}
    We normalize to (B).
    """
    vc = raw.get("voice_candidates")

    # Case A (list)
    if isinstance(vc, list):
        if not vc:
            return {"voice_candidates": {"voice_design_model_uuid": "", "samples": []}}

        # In the guide/API reference, uuid is shared for all samples :contentReference[oaicite:5]{index=5}
        common_uuid = (vc[0] or {}).get("uuid") or ""
        samples = []
        for item in vc:
            if not isinstance(item, dict):
                continue
            samples.append(
                {
                    "audio_url": item.get("audio_url") or "",
                    "sample_index": item.get("voice_sample_index"),
                }
            )
        return {
            "voice_candidates": {
                "voice_design_model_uuid": common_uuid,
                "samples": samples,
            }
        }

    # Case B (dict)
    if isinstance(vc, dict):
        # Just pass through, but ensure keys exist
        return {
            "voice_candidates": {
                "voice_design_model_uuid": vc.get("voice_design_model_uuid") or vc.get("uuid") or "",
                "samples": vc.get("samples") or [],
            }
        }

    # Unknown
    return {"voice_candidates": {"voice_design_model_uuid": "", "samples": []}}


# -------- Voice Cloning --------
def _normalize_voice_type(v: str) -> str:
    """
    Accepts: rapid, professional
    Returns the correct value for Resemble.
    """
    vv = (v or "").strip().lower()
    if vv in ("rapid", "rapid_voice", "rapid-voice"):
        return "rapid"
    return "professional"

def resemble_create_custom_voice(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Wrapper that normalizes voice_type for cloning.
    """
    p = dict(payload or {})
    if "voice_type" in p:
        p["voice_type"] = _normalize_voice_type(p["voice_type"])
    return post_json(f"{RESEMBLE_APP_API_BASE}/api/v2/voices", p, timeout=60)

def resemble_get_voice(uuid: str) -> Dict[str, Any]:
    return get_json(f"{RESEMBLE_APP_API_BASE}/api/v2/voices/{uuid}", timeout=60)

def resemble_upload_voice_recording(
    *,
    voice_uuid: str,
    file_obj: Any,
    filename: str,
    content_type: str,
    name: str,
    text: str = "",
    emotion: str = "neutral",
    is_active: bool = True,
    timeout: int = 120,
) -> Dict[str, Any]:
    """
    POST multipart:
      /api/v2/voices/{voice_uuid}/recordings
      fields: file, name, text, emotion, is_active
    """
    url = f"{RESEMBLE_APP_API_BASE}/api/v2/voices/{voice_uuid}/recordings"
    data = {
        "name": name,
        "text": text,
        "emotion": emotion,
        "is_active": "true" if is_active else "false",
    }
    files = {"file": (filename, file_obj, content_type or "application/octet-stream")}
    return post_multipart(url, data=data, files=files, timeout=timeout)

def resemble_build_voice(*, voice_uuid: str, fill: bool = False, timeout: int = 60) -> Dict[str, Any]:
    """
    POST /api/v2/voices/{uuid}/build
    Body: {"fill": false}
    """
    url = f"{RESEMBLE_APP_API_BASE}/api/v2/voices/{voice_uuid}/build"
    return post_json(url, {"fill": bool(fill)}, timeout=timeout)


# -------- Deepfake Detection --------
def resemble_detect_list(params: Dict[str, Any]) -> Dict[str, Any]:
    allowed = {"page", "page_size"}
    clean = {k: v for k, v in (params or {}).items() if k in allowed and v is not None}
    # Resemble requires page>=1 (docs)
    if "page" not in clean:
        clean["page"] = 1
    return get_json(f"{RESEMBLE_APP_API_BASE}/api/v2/detect", params=clean, timeout=60)

def resemble_detect_create(payload: Dict[str, Any]) -> Dict[str, Any]:
    # Create returns quickly; analysis happens async on Resemble side
    return post_json(f"{RESEMBLE_APP_API_BASE}/api/v2/detect", payload, timeout=60)

def resemble_detect_get(uuid: str) -> Dict[str, Any]:
    return get_json(f"{RESEMBLE_APP_API_BASE}/api/v2/detect/{uuid}", timeout=60)
