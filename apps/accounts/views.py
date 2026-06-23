from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ProfileForm
from .models import User


def profile_detail(request: HttpRequest, username: str) -> HttpResponse:
    profile_user = get_object_or_404(User, username=username)
    return render(request, "accounts/profile_detail.html", {"profile_user": profile_user})


@login_required
def profile_edit(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = ProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect("accounts:profile", username=request.user.username)
    else:
        form = ProfileForm(instance=request.user)
    return render(request, "accounts/profile_edit.html", {"form": form})

