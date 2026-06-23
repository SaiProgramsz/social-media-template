from django.contrib import admin

from .models import Block, Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("id", "reporter", "reason", "content_type", "object_id", "created_at")
    list_filter = ("reason", "content_type", "created_at")
    search_fields = ("details", "object_id", "reporter__username")


@admin.register(Block)
class BlockAdmin(admin.ModelAdmin):
    list_display = ("id", "blocker", "blocked", "created_at")
    search_fields = ("blocker__username", "blocked__username")

