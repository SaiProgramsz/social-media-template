from __future__ import annotations

from django.apps import apps
from django.contrib.auth import get_user_model
from django.db.models.signals import post_migrate
from django.dispatch import receiver


@receiver(post_migrate)
def seed_welcome_post(sender, app_config=None, **kwargs):
    if not app_config or app_config.label != "feed":
        return

    Post = apps.get_model("feed", "Post")
    User = get_user_model()

    if Post.objects.exists():
        return

    system_user, _ = User.objects.get_or_create(
        username="studynet",
        defaults={"display_name": "study.net", "is_active": True},
    )
    if not system_user.has_usable_password():
        system_user.set_unusable_password()
        system_user.save(update_fields=["password"])

    Post.objects.create(
        author=system_user,
        subject="Welcome",
        text=(
            "Welcome to study.net.\n\n"
            "Post what you studied today (a short summary, a tip, or a resource link). "
            "Keep it kind and focused—this is a learning-first community."
        ),
    )

