from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Block",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "blocked",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="blocks_received", to=settings.AUTH_USER_MODEL),
                ),
                (
                    "blocker",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="blocks_made", to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={"unique_together": {("blocker", "blocked")}},
        ),
        migrations.CreateModel(
            name="Report",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("reason", models.CharField(max_length=80)),
                ("details", models.TextField(blank=True)),
                ("content_type", models.CharField(help_text="e.g. post, room, note, question, answer, user", max_length=40)),
                ("object_id", models.CharField(help_text="String to support multiple id types", max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "reporter",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="reports_made", to=settings.AUTH_USER_MODEL),
                ),
            ],
        ),
    ]

