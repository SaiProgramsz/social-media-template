from __future__ import annotations

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    display_name = models.CharField(max_length=60, blank=True)
    school = models.CharField(max_length=120, blank=True)
    major = models.CharField(max_length=120, blank=True)
    grade_level = models.CharField(max_length=40, blank=True)
    bio = models.TextField(blank=True)
    profile_image = models.ImageField(upload_to="profiles/", blank=True, null=True)
    is_minor = models.BooleanField(default=False)

    def safe_name(self) -> str:
        return self.display_name or self.get_username()
