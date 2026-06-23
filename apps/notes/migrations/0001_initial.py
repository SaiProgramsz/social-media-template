from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="NoteSet",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=140)),
                ("subject", models.CharField(blank=True, max_length=80)),
                ("content", models.TextField(help_text="Markdown/plain text supported (render later).")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "author",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="note_sets", to=settings.AUTH_USER_MODEL),
                ),
            ],
        ),
    ]

