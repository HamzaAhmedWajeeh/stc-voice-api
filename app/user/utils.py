from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken
from datetime import datetime, timedelta, timezone as dt_timezone

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError

from rest_framework import serializers


# ----------------------------
# Tunables
# ----------------------------
RESET_TOKEN_TTL_MINUTES = getattr(settings, "RESET_TOKEN_TTL_MINUTES", 15)



def generate_key():
    return Fernet.generate_key()


def get_client_ip(request) -> str:
    """
    Basic IP extraction. If you’re behind a proxy/LB, ensure Django is configured
    to trust X-Forwarded-For correctly, or use django-ipware.
    """
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR") or ""


def encrypt_email(email: str, key) -> bytes:
    """
    Encrypts: "<email>--<ISO8601 UTC timestamp>" using Fernet.
    Uses timezone-aware UTC timestamp.
    """
    if not email:
        raise ValueError("email is required")

    now_utc_iso = timezone.now().astimezone(dt_timezone.utc).isoformat()
    payload = f"{email}--{now_utc_iso}"

    cipher_suite = Fernet(_to_bytes(key))
    return cipher_suite.encrypt(payload.encode("utf-8"))


def decrypt_email(encrypted_email, key) -> str | None:
    """
    Accepts str or bytes token. Returns email if token is valid and not expired,
    otherwise returns None. Safe: does not raise InvalidToken.
    """
    if not encrypted_email:
        return None

    cipher_suite = Fernet(_to_bytes(key))
    token_bytes = _to_bytes(encrypted_email)

    try:
        decrypted = cipher_suite.decrypt(token_bytes)
    except (InvalidToken, Exception):
        return None

    try:
        decrypted_text = decrypted.decode("utf-8")
        email, ts = decrypted_text.rsplit("--", 1)
        dt = datetime.fromisoformat(ts)
    except Exception:
        return None

    # Normalize datetime to aware UTC
    if timezone.is_naive(dt):
        dt = dt.replace(tzinfo=dt_timezone.utc)
    else:
        dt = dt.astimezone(dt_timezone.utc)

    now_utc = timezone.now().astimezone(dt_timezone.utc)

    # Expiration window (default 15 minutes)
    if dt + timedelta(minutes=RESET_TOKEN_TTL_MINUTES) > now_utc:
        return email

    return None


def _validate_password_strength(password: str, *, user=None):
    """
    Run Django's AUTH_PASSWORD_VALIDATORS and raise DRF-friendly errors.
    """
    try:
        validate_password(password=password, user=user)
    except DjangoValidationError as e:
        raise serializers.ValidationError(list(e.messages))
