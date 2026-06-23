from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class AppUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Student profile", {"fields": ("display_name", "school", "major", "grade_level", "bio", "is_minor")}),
    )

