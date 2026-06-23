from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static

from apps.core import views as core_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", core_views.home, name="home"),
    # Override Django's built-in logout to avoid HTTP 405 when browsers hit it via GET.
    path("accounts/logout/", core_views.logout_view, name="logout"),
    path("accounts/", include("django.contrib.auth.urls")),
    path("u/", include("apps.accounts.urls")),
    path("mod/", include("apps.moderation.urls")),
    path("planner/", include("apps.planner.urls")),
    path("feed/", include("apps.feed.urls")),
    path("rooms/", include("apps.rooms.urls")),
    path("notes/", include("apps.notes.urls")),
    path("qa/", include("apps.qa.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
