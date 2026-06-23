from django.contrib.auth import logout
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render

from apps.feed.models import Post
from apps.rooms.models import StudyRoom


def home(request: HttpRequest) -> HttpResponse:
    posts = Post.objects.select_related("author").order_by("-created_at")[:20]
    rooms = StudyRoom.objects.order_by("-created_at")[:8]
    return render(request, "home.html", {"posts": posts, "rooms": rooms})


def logout_view(request: HttpRequest) -> HttpResponse:
    # Django's built-in LogoutView can be POST-only in newer versions.
    # Support GET here so old cached links (or direct navigation) won't 405.
    if request.user.is_authenticated:
        logout(request)
    return redirect("home")
