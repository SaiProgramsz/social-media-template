from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Post",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("subject", models.CharField(blank=True, max_length=80)),
                ("text", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "author",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="posts", to=settings.AUTH_USER_MODEL),
                ),
            ],
        ),
        migrations.AddIndex(
            model_name="post",
            index=models.Index(fields=["-created_at"], name="feed_post_created_3d8f05_idx"),
        ),
    ]

