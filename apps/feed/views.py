from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import PostForm
from .models import Post


def feed(request: HttpRequest) -> HttpResponse:
    posts = Post.objects.select_related("author").order_by("-created_at")[:50]
    return render(request, "feed/feed.html", {"posts": posts})


@login_required
def create_post(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = PostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            return redirect("feed:feed")
    else:
        form = PostForm()
    return render(request, "feed/create_post.html", {"form": form})


@login_required
def delete_post(request: HttpRequest, post_id: int) -> HttpResponse:
    post = get_object_or_404(Post, id=post_id)
    if not (request.user.is_staff or post.author_id == request.user.id):
        return redirect("feed:feed")
    if request.method == "POST":
        post.delete()
        return redirect("feed:feed")
    return render(request, "confirm_delete.html", {"title": "Delete post", "object_name": "post"})
