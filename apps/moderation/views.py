from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.accounts.models import User

from .forms import BlockForm, ReportForm
from .models import Block, Report


@login_required
def report(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = ReportForm(request.POST)
        if form.is_valid():
            r: Report = form.save(commit=False)
            r.reporter = request.user
            r.save()
            messages.success(request, "Thanks — your report was submitted.")
            return redirect("home")
    else:
        initial = {
            "content_type": request.GET.get("type", ""),
            "object_id": request.GET.get("id", ""),
        }
        form = ReportForm(initial=initial)
    return render(request, "moderation/report.html", {"form": form})


@login_required
def block_user(request: HttpRequest, username: str) -> HttpResponse:
    target = get_object_or_404(User, username=username)
    if target.id == request.user.id:
        return redirect("accounts:profile", username=request.user.username)
    if request.method == "POST":
        Block.objects.get_or_create(blocker=request.user, blocked=target)
        messages.success(request, f"You blocked @{target.username}.")
        return redirect("accounts:profile", username=target.username)
    form = BlockForm()
    return render(request, "moderation/block_confirm.html", {"target": target, "form": form})


@login_required
def reports_dashboard(request: HttpRequest) -> HttpResponse:
    if not request.user.is_staff:
        return redirect("home")
    reports = Report.objects.select_related("reporter").order_by("-created_at")[:200]
    return render(request, "moderation/reports_dashboard.html", {"reports": reports, "now": timezone.now()})
