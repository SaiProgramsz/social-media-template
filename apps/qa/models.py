from __future__ import annotations

from django.conf import settings
from django.db import models


class Question(models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="questions")
    subject = models.CharField(max_length=80, blank=True)
    title = models.CharField(max_length=160)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.title


class Answer(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="answers")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="answers")
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

