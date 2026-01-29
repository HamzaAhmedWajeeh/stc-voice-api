"""
Database models.
"""
from __future__ import annotations

import uuid as uuid_lib

from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin
)
from django.conf import settings

import hashlib



class UserManager(BaseUserManager):
    """Manager for users."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email must be provided.')
        user = self.model(email=self.normalize_email(email), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and return a new superuser."""
        user = self.create_user(email, password=password, **extra_fields)
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)

        return user


class User(AbstractBaseUser, PermissionsMixin):
    """User in the system."""
    email = models.EmailField(max_length=255, unique=True)
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    verified = models.BooleanField(default=False)
    verification_token = models.CharField(max_length=64, blank=True, null=True)
    last_login = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

    def generate_verification_token(self):
        data_to_hash = f"{self.email}{settings.SECRET_KEY}"
        self.verification_token = hashlib.sha256(
            data_to_hash.encode()
            ).hexdigest()
        self.save()

    @staticmethod
    def get_user_by_verification_token(verification_token):
        try:
            return User.objects.get(verification_token=verification_token)
        except User.DoesNotExist:
            return None


class DeepfakeUpload(models.Model):
    """
    Stores an uploaded media file that will be analyzed by Resemble.
    Must be publicly reachable via HTTPS for Resemble to fetch.
    """
    uuid = models.UUIDField(primary_key=True, default=uuid_lib.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="deepfake_uploads")

    file = models.FileField(upload_to="deepfake/%Y%m%d/")
    original_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=120, blank=True)
    size_bytes = models.BigIntegerField(default=0)
    sha256 = models.CharField(max_length=64, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.uuid} ({self.original_name})"


class DeepfakeDetectJob(models.Model):
    """
    Tracks an async request to create a Resemble detect job.
    """
    class Status(models.TextChoices):
        QUEUED = "queued"
        RUNNING = "running"
        SUCCEEDED = "succeeded"
        FAILED = "failed"

    uuid = models.UUIDField(primary_key=True, default=uuid_lib.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="deepfake_detect_jobs")
    upload = models.ForeignKey(DeepfakeUpload, on_delete=models.CASCADE, related_name="detect_jobs")

    status = models.CharField(max_length=16, choices=Status.choices, default=Status.QUEUED)
    celery_task_id = models.CharField(max_length=128, blank=True)

    # Returned by Resemble after create:
    remote_detect_uuid = models.CharField(max_length=64, blank=True)

    request_payload = models.JSONField(default=dict, blank=True)
    create_response = models.JSONField(default=dict, blank=True)

    error_message = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
