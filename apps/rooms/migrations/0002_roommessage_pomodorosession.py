from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        ("rooms", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="PomodoroSession",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("focus_minutes", models.PositiveSmallIntegerField(default=25)),
                ("break_minutes", models.PositiveSmallIntegerField(default=5)),
                ("started_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("ended_at", models.DateTimeField(blank=True, null=True)),
                ("note", models.CharField(blank=True, max_length=140)),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="created_pomodoro_sessions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "room",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, related_name="pomodoro_sessions", to="rooms.studyroom"
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="RoomMessage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("text", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "author",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, related_name="room_messages", to=settings.AUTH_USER_MODEL
                    ),
                ),
                (
                    "room",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, related_name="messages", to="rooms.studyroom"
                    ),
                ),
            ],
        ),
        migrations.AddIndex(
            model_name="pomodorosession",
            index=models.Index(fields=["room", "-started_at"], name="rooms_pomodoro_room_id_1dd2ac_idx"),
        ),
        migrations.AddIndex(
            model_name="roommessage",
            index=models.Index(fields=["room", "-created_at"], name="rooms_roommsg_room_id_78fb6e_idx"),
        ),
    ]

