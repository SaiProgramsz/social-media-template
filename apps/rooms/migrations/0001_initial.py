from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="StudyRoom",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=120)),
                ("subject", models.CharField(blank=True, max_length=80)),
                ("description", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "creator",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="created_rooms", to=settings.AUTH_USER_MODEL),
                ),
            ],
        ),
        migrations.CreateModel(
            name="RoomMembership",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("joined_at", models.DateTimeField(auto_now_add=True)),
                ("room", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="memberships", to="rooms.studyroom")),
                (
                    "user",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="room_memberships", to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={"unique_together": {("room", "user")}},
        ),
    ]

