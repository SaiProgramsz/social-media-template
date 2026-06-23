from __future__ import annotations

from django.conf import settings
from django.db import models


class NoteSet(models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="note_sets")
    title = models.CharField(max_length=140)
    subject = models.CharField(max_length=80, blank=True)
    content = models.TextField(help_text="Markdown/plain text supported (render later).")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.title

