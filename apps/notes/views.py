from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import NoteSetForm
from .models import NoteSet


def note_list(request: HttpRequest) -> HttpResponse:
    notes = NoteSet.objects.select_related("author").order_by("-created_at")[:50]
    return render(request, "notes/notes.html", {"notes": notes})


def note_detail(request: HttpRequest, note_id: int) -> HttpResponse:
    note = get_object_or_404(NoteSet.objects.select_related("author"), id=note_id)
    return render(request, "notes/detail.html", {"note": note})


@login_required
def create_note(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = NoteSetForm(request.POST)
        if form.is_valid():
            note = form.save(commit=False)
            note.author = request.user
            note.save()
            return redirect("notes:detail", note_id=note.id)
    else:
        form = NoteSetForm()
    return render(request, "notes/create_note.html", {"form": form})

