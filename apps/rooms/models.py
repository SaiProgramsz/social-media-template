from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone


class StudyRoom(models.Model):
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="created_rooms")
    title = models.CharField(max_length=120)
    subject = models.CharField(max_length=80, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.title


class RoomMembership(models.Model):
    room = models.ForeignKey(StudyRoom, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="room_memberships")
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("room", "user")]


class PomodoroSession(models.Model):
    room = models.ForeignKey(StudyRoom, on_delete=models.CASCADE, related_name="pomodoro_sessions")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="created_pomodoro_sessions"
    )
    focus_minutes = models.PositiveSmallIntegerField(default=25)
    break_minutes = models.PositiveSmallIntegerField(default=5)
    started_at = models.DateTimeField(default=timezone.now)
    ended_at = models.DateTimeField(blank=True, null=True)
    note = models.CharField(max_length=140, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["room", "-started_at"]),
        ]

    @property
    def is_active(self) -> bool:
        return self.ended_at is None


class RoomMessage(models.Model):
    room = models.ForeignKey(StudyRoom, on_delete=models.CASCADE, related_name="messages")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="room_messages")
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["room", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"RoomMessage({self.room_id}, {self.author_id})"
