from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import PomodoroSessionForm, RoomMessageForm, StudyRoomForm
from .models import PomodoroSession, RoomMembership, RoomMessage, StudyRoom


def room_list(request: HttpRequest) -> HttpResponse:
    rooms = StudyRoom.objects.order_by("-created_at")[:50]
    return render(request, "rooms/rooms.html", {"rooms": rooms})


@login_required
def create_room(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = StudyRoomForm(request.POST)
        if form.is_valid():
            room = form.save(commit=False)
            room.creator = request.user
            room.save()
            RoomMembership.objects.get_or_create(room=room, user=request.user)
            return redirect("rooms:detail", room_id=room.id)
    else:
        form = StudyRoomForm()
    return render(request, "rooms/create_room.html", {"form": form})


def room_detail(request: HttpRequest, room_id: int) -> HttpResponse:
    room = get_object_or_404(StudyRoom, id=room_id)
    is_member = False
    if request.user.is_authenticated:
        is_member = RoomMembership.objects.filter(room=room, user=request.user).exists()
    active_session = PomodoroSession.objects.filter(room=room, ended_at__isnull=True).order_by("-started_at").first()
    messages = RoomMessage.objects.select_related("author").filter(room=room).order_by("-created_at")[:50]
    message_form = RoomMessageForm()
    pomodoro_form = PomodoroSessionForm()
    return render(
        request,
        "rooms/detail.html",
        {
            "room": room,
            "is_member": is_member,
            "can_manage_room": request.user.is_authenticated and (request.user.is_staff or room.creator_id == request.user.id),
            "active_session": active_session,
            "messages": list(reversed(messages)),
            "message_form": message_form,
            "pomodoro_form": pomodoro_form,
        },
    )


@login_required
def join_room(request: HttpRequest, room_id: int) -> HttpResponse:
    room = get_object_or_404(StudyRoom, id=room_id)
    RoomMembership.objects.get_or_create(room=room, user=request.user)
    return redirect("rooms:detail", room_id=room.id)


@login_required
def send_message(request: HttpRequest, room_id: int) -> HttpResponse:
    room = get_object_or_404(StudyRoom, id=room_id)
    if not RoomMembership.objects.filter(room=room, user=request.user).exists():
        return redirect("rooms:detail", room_id=room.id)
    if request.method != "POST":
        return redirect("rooms:detail", room_id=room.id)
    form = RoomMessageForm(request.POST)
    if form.is_valid():
        msg = form.save(commit=False)
        msg.room = room
        msg.author = request.user
        msg.save()
    return redirect("rooms:detail", room_id=room.id)


@login_required
def start_pomodoro(request: HttpRequest, room_id: int) -> HttpResponse:
    room = get_object_or_404(StudyRoom, id=room_id)
    if not RoomMembership.objects.filter(room=room, user=request.user).exists():
        return redirect("rooms:detail", room_id=room.id)
    if request.method != "POST":
        return redirect("rooms:detail", room_id=room.id)

    if PomodoroSession.objects.filter(room=room, ended_at__isnull=True).exists():
        return redirect("rooms:detail", room_id=room.id)

    form = PomodoroSessionForm(request.POST)
    if form.is_valid():
        session = form.save(commit=False)
        session.room = room
        session.created_by = request.user
        session.save()
    return redirect("rooms:detail", room_id=room.id)


@login_required
def end_pomodoro(request: HttpRequest, room_id: int, session_id: int) -> HttpResponse:
    room = get_object_or_404(StudyRoom, id=room_id)
    if request.method != "POST":
        return redirect("rooms:detail", room_id=room.id)
    session = get_object_or_404(PomodoroSession, id=session_id, room=room)
    if not RoomMembership.objects.filter(room=room, user=request.user).exists():
        return redirect("rooms:detail", room_id=room.id)
    if session.ended_at is None:
        from django.utils import timezone

        session.ended_at = timezone.now()
        session.save(update_fields=["ended_at"])
    return redirect("rooms:detail", room_id=room.id)


@login_required
def delete_room(request: HttpRequest, room_id: int) -> HttpResponse:
    room = get_object_or_404(StudyRoom, id=room_id)
    if not (request.user.is_staff or room.creator_id == request.user.id):
        return redirect("rooms:detail", room_id=room.id)
    if request.method == "POST":
        room.delete()
        return redirect("rooms:list")
    return render(
        request,
        "confirm_delete.html",
        {"title": "Delete room", "object_name": f'room "{room.title}"'},
    )
