import logging
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.conf import settings

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer

from .utils import _validate_password_strength

logger = logging.getLogger(__name__)
User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    last_seen = serializers.DateTimeField(source="last_login", read_only=True, allow_null=True)

    class Meta:
        model = User
        fields = ["id", "email", "password", "name", "status", "last_seen"]
        read_only_fields = ["id", "status", "last_seen"]
        extra_kwargs = {"password": {"write_only": True}}

    def validate_password(self, value: str) -> str:
        user_obj = self.instance
        if user_obj is None:
            user_obj = User(
                email=(self.initial_data.get("email") or ""),
                name=(self.initial_data.get("name") or ""),
            )
        _validate_password_strength(value, user=user_obj)
        return value

    def get_status(self, obj) -> str:
        return "Inactive" if (obj.is_active is False) else "Active"

    def update(self, instance, validated_data):
        if "email" in validated_data:
            raise serializers.ValidationError("Email cannot be changed.")

        password = validated_data.pop("password", None)
        user = super().update(instance, validated_data)

        if password:
            user.set_password(password)
            user.save(update_fields=["password"])

        return user


class CookieTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Adds checks:
    - verified must be True
    - is_active must be True
    """
    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user

        if not user.verified or not user.is_active:
            from rest_framework.exceptions import AuthenticationFailed
            raise AuthenticationFailed("Your email is not verified or your account is inactive.")

        user.last_login = timezone.now()
        user.save(update_fields=["last_login"])

        return data


class CookieTokenRefreshSerializer(TokenRefreshSerializer):
    """
    Accept refresh token from cookie instead of request body.
    """
    def validate(self, attrs):
        refresh_cookie = getattr(settings, "JWT_REFRESH_COOKIE_NAME", "refresh_token")
        cookie_refresh = self.context["request"].COOKIES.get(refresh_cookie)
        if not cookie_refresh:
            raise serializers.ValidationError({"detail": "Refresh cookie not found."})
        attrs["refresh"] = cookie_refresh
        return super().validate(attrs)


class EmptySerializer(serializers.Serializer):
    pass


class CreateUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["email", "password", "name"]
        extra_kwargs = {
            "password": {"write_only": True, "min_length": 5},
        }

    def validate_password(self, value: str) -> str:
        temp_user = User(
            email=(self.initial_data.get("email") or ""),
            name=(self.initial_data.get("name") or ""),
        )
        _validate_password_strength(value, user=temp_user)
        return value

    def validate_email(self, value: str) -> str:
        value = (value or "").strip().lower()
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("This email is already in use.")
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")

        # Force single-user flags
        validated_data["verified"] = True
        validated_data["is_active"] = True

        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save(update_fields=["password"])
        return user
