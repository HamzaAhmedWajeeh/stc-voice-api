import logging

from django.conf import settings
from django.middleware.csrf import get_token

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .serializers import (
    UserSerializer,
    CookieTokenObtainPairSerializer,
    CookieTokenRefreshSerializer,
    EmptySerializer,
    CreateUserSerializer
)

logger = logging.getLogger(__name__)


def _cookie_kwargs(*, max_age: int | None, path: str, httponly: bool) -> dict:
    return {
        "max_age": max_age,
        "httponly": httponly,
        "secure": getattr(settings, "JWT_COOKIE_SECURE", True),
        "samesite": getattr(settings, "JWT_COOKIE_SAMESITE", "None"),
        "domain": getattr(settings, "JWT_COOKIE_DOMAIN", None),
        "path": path,
    }


class CreateTokenView(TokenObtainPairView):
    serializer_class = CookieTokenObtainPairSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        access = serializer.validated_data.get("access")
        refresh = serializer.validated_data.get("refresh")

        if not access or not refresh:
            return Response({"detail": "Token generation failed."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        user = serializer.user

        resp = Response(
            {"detail": "Login successful", "verified": bool(user.verified), "is_active": bool(user.is_active)},
            status=status.HTTP_200_OK,
        )

        access_cookie = getattr(settings, "JWT_ACCESS_COOKIE_NAME", "access_token")
        refresh_cookie = getattr(settings, "JWT_REFRESH_COOKIE_NAME", "refresh_token")

        resp.set_cookie(
            access_cookie,
            access,
            **_cookie_kwargs(
                max_age=10 * 60,
                path=getattr(settings, "JWT_ACCESS_COOKIE_PATH", "/"),
                httponly=True,
            ),
        )

        resp.set_cookie(
            refresh_cookie,
            refresh,
            **_cookie_kwargs(
                max_age=7 * 24 * 60 * 60,
                path=getattr(settings, "JWT_REFRESH_COOKIE_PATH", "/api/auth/"),
                httponly=True,
            ),
        )

        # Ensure CSRF cookie is set (Django will send csrftoken cookie)
        get_token(request)
        return resp


class RefreshView(TokenRefreshView):
    serializer_class = CookieTokenRefreshSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        resp = super().post(request, *args, **kwargs)

        access = resp.data.get("access")
        new_refresh = resp.data.get("refresh")

        resp.data = {"detail": "Refreshed"}

        resp.set_cookie(
            getattr(settings, "JWT_ACCESS_COOKIE_NAME", "access_token"),
            access,
            **_cookie_kwargs(
                max_age=10 * 60,
                path=getattr(settings, "JWT_ACCESS_COOKIE_PATH", "/"),
                httponly=True,
            ),
        )

        if new_refresh:
            resp.set_cookie(
                getattr(settings, "JWT_REFRESH_COOKIE_NAME", "refresh_token"),
                new_refresh,
                **_cookie_kwargs(
                    max_age=7 * 24 * 60 * 60,
                    path=getattr(settings, "JWT_REFRESH_COOKIE_PATH", "/api/auth/"),
                    httponly=True,
                ),
            )

        get_token(request)
        return resp


class LogoutView(APIView):
    serializer_class = EmptySerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        refresh_cookie = getattr(settings, "JWT_REFRESH_COOKIE_NAME", "refresh_token")
        token_str = request.COOKIES.get(refresh_cookie)

        if token_str:
            try:
                RefreshToken(token_str).blacklist()
            except Exception:
                pass

        resp = Response({"detail": "Logged out"}, status=status.HTTP_200_OK)

        # Clear cookies (must match same domain/path used when set)
        resp.delete_cookie(
            getattr(settings, "JWT_ACCESS_COOKIE_NAME", "access_token"),
            path=getattr(settings, "JWT_ACCESS_COOKIE_PATH", "/"),
            domain=getattr(settings, "JWT_COOKIE_DOMAIN", None),
        )
        resp.delete_cookie(
            getattr(settings, "JWT_REFRESH_COOKIE_NAME", "refresh_token"),
            path=getattr(settings, "JWT_REFRESH_COOKIE_PATH", "/api/auth/"),
            domain=getattr(settings, "JWT_COOKIE_DOMAIN", None),
        )

        return resp


class ManageUserView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class CreateUserView(generics.CreateAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = CreateUserSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        return Response(
            {
                "detail": "User created",
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "name": user.name,
                    "verified": bool(user.verified),
                    "is_active": bool(user.is_active),
                },
            },
            status=status.HTTP_201_CREATED,
        )
