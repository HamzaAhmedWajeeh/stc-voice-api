import logging
from http.cookies import SimpleCookie
from typing import Optional, Dict

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware

from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import TokenError

logger = logging.getLogger(__name__)
User = get_user_model()


def _headers(scope) -> Dict[bytes, bytes]:
    out: Dict[bytes, bytes] = {}
    for k, v in (scope.get("headers") or []):
        try:
            out[k.lower()] = v
        except Exception:
            continue
    return out


def _get_cookie_value(scope, name: str) -> Optional[str]:
    hdrs = _headers(scope)
    raw = hdrs.get(b"cookie")
    if not raw:
        return None
    try:
        cookie = SimpleCookie()
        cookie.load(raw.decode("utf-8", errors="ignore"))
        morsel = cookie.get(name)
        return morsel.value if morsel else None
    except Exception:
        return None


def _get_bearer_token(scope) -> Optional[str]:
    hdrs = _headers(scope)
    raw = hdrs.get(b"authorization")
    if not raw:
        return None
    try:
        val = raw.decode("utf-8", errors="ignore").strip()
        if val.lower().startswith("bearer "):
            return val.split(" ", 1)[1].strip()
    except Exception:
        return None
    return None


@database_sync_to_async
def _get_user_by_id(user_id: int):
    try:
        return User.objects.get(pk=user_id)
    except Exception:
        return AnonymousUser()


class CookieJWTAuthMiddleware(BaseMiddleware):
    """
    WebSocket auth:
      - Prefer HttpOnly cookie JWT (access_token)
      - Optionally allow Authorization: Bearer <jwt> if WS_ALLOW_AUTH_HEADER=True
    """

    async def __call__(self, scope, receive, send):
        scope = dict(scope)

        cookie_name = getattr(settings, "JWT_ACCESS_COOKIE_NAME", "access_token")
        allow_header = bool(getattr(settings, "WS_ALLOW_AUTH_HEADER", False))

        raw_token = _get_cookie_value(scope, cookie_name)
        token_source = "cookie" if raw_token else None

        if not raw_token and allow_header:
            raw_token = _get_bearer_token(scope)
            token_source = "authorization" if raw_token else None

        if not raw_token:
            scope["user"] = AnonymousUser()
            scope["jwt_error"] = "missing_token"
            scope["jwt_source"] = None
            return await super().__call__(scope, receive, send)

        try:
            token = AccessToken(raw_token)
            user_id = token.get("user_id")
            if not user_id:
                scope["user"] = AnonymousUser()
                scope["jwt_error"] = "missing_user_id"
                scope["jwt_source"] = token_source
                return await super().__call__(scope, receive, send)

            user = await _get_user_by_id(int(user_id))
            if not getattr(user, "is_authenticated", False):
                scope["user"] = AnonymousUser()
                scope["jwt_error"] = "user_not_found"
                scope["jwt_source"] = token_source
                return await super().__call__(scope, receive, send)

            scope["user"] = user
            scope["jwt_error"] = None
            scope["jwt_source"] = token_source
            scope["jwt"] = {
                "jti": token.get("jti"),
                "exp": token.get("exp"),
                "user_id": int(user_id),
                "token_type": token.get("token_type"),
            }

        except TokenError:
            scope["user"] = AnonymousUser()
            scope["jwt_error"] = "invalid_or_expired"
            scope["jwt_source"] = token_source
        except Exception:
            logger.exception("CookieJWTAuthMiddleware unexpected error")
            scope["user"] = AnonymousUser()
            scope["jwt_error"] = "unexpected"
            scope["jwt_source"] = token_source

        return await super().__call__(scope, receive, send)


def CookieJWTAuthMiddlewareStack(inner):
    return CookieJWTAuthMiddleware(inner)
