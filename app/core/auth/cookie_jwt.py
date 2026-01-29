from __future__ import annotations

from django.conf import settings
from django.middleware.csrf import CsrfViewMiddleware

from drf_spectacular.extensions import OpenApiAuthenticationExtension

from rest_framework import exceptions
from rest_framework_simplejwt.authentication import JWTAuthentication


class CookieJWTAuthentication(JWTAuthentication):
    """
    - Reads access JWT from HttpOnly cookie (preferred for browsers)
    - Falls back to Authorization: Bearer <token> (useful for CLI/Postman)
    - Enforces CSRF for unsafe methods IF token came from cookie
    """

    def authenticate(self, request):
        access_cookie = getattr(settings, "JWT_ACCESS_COOKIE_NAME", "access_token")
        raw_token = request.COOKIES.get(access_cookie)

        if raw_token:
            self._enforce_csrf(request)
            validated_token = self.get_validated_token(raw_token)
            return self.get_user(validated_token), validated_token

        return super().authenticate(request)

    def _enforce_csrf(self, request):
        if request.method in ("GET", "HEAD", "OPTIONS", "TRACE", "POST", "PUT", "PATCH", "DELETE"):
            return

        # Use Django's CSRF middleware validation
        reason = CsrfViewMiddleware(lambda req: None).process_view(request, None, (), {})
        if reason:
            raise exceptions.PermissionDenied(f"CSRF Failed: {reason}")


class CookieJWTAuthenticationScheme(OpenApiAuthenticationExtension):
    """
    Teach drf-spectacular how to document CookieJWTAuthentication.

    We describe it as an apiKey stored in a cookie (OpenAPI supports cookie apiKey).
    """
    target_class = "core.auth.cookie_jwt.CookieJWTAuthentication"
    name = "cookieJWT"

    def get_security_definition(self, auto_schema):
        cookie_name = getattr(settings, "JWT_ACCESS_COOKIE_NAME", "access_token")
        return {
            "type": "apiKey",
            "in": "cookie",
            "name": cookie_name,
        }
