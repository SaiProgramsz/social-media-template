from django.contrib import admin

from .models import PomodoroSession, RoomMembership, RoomMessage, StudyRoom


@admin.register(StudyRoom)
class StudyRoomAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "subject", "creator", "created_at")
    list_filter = ("subject", "created_at")
    search_fields = ("title", "description", "creator__username")


@admin.register(RoomMembership)
class RoomMembershipAdmin(admin.ModelAdmin):
    list_display = ("id", "room", "user", "joined_at")
    list_filter = ("joined_at",)
    search_fields = ("room__title", "user__username")


@admin.register(RoomMessage)
class RoomMessageAdmin(admin.ModelAdmin):
    list_display = ("id", "room", "author", "created_at", "preview")
    list_filter = ("created_at", "room")
    search_fields = ("text", "author__username", "room__title")

    @admin.display(description="Text")
    def preview(self, obj: RoomMessage) -> str:
        t = (obj.text or "").strip()
        return t[:80] + ("…" if len(t) > 80 else "")


@admin.register(PomodoroSession)
class PomodoroSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "room", "created_by", "focus_minutes", "break_minutes", "started_at", "ended_at")
    list_filter = ("started_at", "ended_at", "room")
    search_fields = ("room__title", "created_by__username", "note")

