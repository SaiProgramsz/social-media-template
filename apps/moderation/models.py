from __future__ import annotations

from django.conf import settings
from django.db import models


class Block(models.Model):
    blocker = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="blocks_made")
    blocked = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="blocks_received")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("blocker", "blocked")]


class Report(models.Model):
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reports_made")
    reason = models.CharField(max_length=80)
    details = models.TextField(blank=True)
    content_type = models.CharField(max_length=40, help_text="e.g. post, room, note, question, answer, user")
    object_id = models.CharField(max_length=64, help_text="String to support multiple id types")
    created_at = models.DateTimeField(auto_now_add=True)

